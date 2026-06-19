#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import sys
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import quote, urlsplit


def _default_app_path() -> Path:
    return Path(__file__).resolve().parents[2] / "apps" / "api"


APP_PATH = Path(os.environ.get("CORP_APP_PATH", str(_default_app_path())))
if str(APP_PATH) not in sys.path:
    sys.path.insert(0, str(APP_PATH))

try:
    from app.subscription.display_names import NAME_MODE_BLANC
    from app.subscription.display_names import NAME_MODE_SLOVO
    from app.subscription.pipeline import build_subscription_response
    from app.subscription.render import BYPASS_RENDER_SOCKS
    from app.subscription.slovo_ru_direct import parse_slovo_ru_direct_routes
    from app.subscription.ua import FORMAT_HAPP, OUTPUT_FORMAT_AUTO, resolve_output_format
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Cannot import Iter subscription modules. Set CORP_APP_PATH to the apps/api directory."
    ) from exc


CORP_SLOTS = frozenset({1, 2, 3, 4})
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_CACHE_TTL = 300
DEFAULT_PROFILE_PREFIX = "CORP VPN"
DEFAULT_ROUTE_NAME = "CORP Route"
DEFAULT_CLASH_GROUP_NAME = "CORP VPN"


@dataclass
class CachedResponse:
    media_type: str
    body: bytes
    headers: dict[str, str]
    created_at: float


_cache: dict[tuple[object, ...], CachedResponse] = {}
_lock = Lock()


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _cache_ttl() -> int:
    raw = os.environ.get("CORP_CACHE_TTL")
    if not raw:
        return DEFAULT_CACHE_TTL
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_CACHE_TTL


def _profile_title(slot: int, *, deactivated: bool) -> str:
    if deactivated:
        return "Подписка деактивирована"
    prefix = os.environ.get("CORP_PROFILE_PREFIX", DEFAULT_PROFILE_PREFIX).strip() or DEFAULT_PROFILE_PREFIX
    return f"{prefix} | {slot}"


def _content_disposition_filename(filename: str) -> str:
    try:
        filename.encode("latin-1")
    except UnicodeEncodeError:
        encoded = quote(filename.encode("utf-8"))
        return f'attachment; filename="subscription"; filename*=UTF-8\'\'{encoded}'
    return f'attachment; filename="{filename}"'


def _corp_headers(slot: int, *, deactivated: bool, extra: dict[str, str]) -> dict[str, str]:
    title = _profile_title(slot, deactivated=deactivated)
    title_b64 = base64.b64encode(title.encode("utf-8")).decode("ascii")
    headers = {
        "Cache-Control": "no-store",
        "profile-title": f"base64:{title_b64}",
        "profile-update-interval": "1",
        "Content-Disposition": _content_disposition_filename(title),
        "X-Content-Type-Options": "nosniff",
    }
    if "routing" in extra:
        headers["routing"] = extra["routing"]
    return headers


def _slot_from_path(path: str) -> int | None:
    clean_path = urlsplit(path).path
    prefix = "/CorpVpnSubscription"
    suffix = "_"
    if not clean_path.startswith(prefix) or not clean_path.endswith(suffix):
        return None
    raw = clean_path[len(prefix) : -len(suffix)]
    try:
        slot = int(raw)
    except ValueError:
        return None
    return slot if slot in CORP_SLOTS else None


def _master_url_for_slot(slot: int) -> str:
    url = (
        os.environ.get(f"CORP_MASTER_SUBSCRIPTION_URL_{slot}")
        or os.environ.get(f"CORP_MASTER_URL_{slot}")
        or os.environ.get("CORP_MASTER_SUBSCRIPTION_URL")
        or os.environ.get("CORP_MASTER_URL")
        or ""
    ).strip()
    if not url:
        raise RuntimeError("CORP_MASTER_SUBSCRIPTION_URL is not set")
    return url


def _state_file() -> Path:
    raw = os.environ.get("CORP_SLOT_STATE_FILE")
    if raw:
        return Path(raw)
    if os.name == "nt":
        return Path(__file__).resolve().with_name("corpvpn-slot-state.json")
    return Path("/var/lib/corpvpn/slot-state.json")


def _load_state_doc() -> dict[str, Any]:
    path = _state_file()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_state_doc(doc: dict[str, Any]) -> None:
    path = _state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        print(f"Cannot save CORP slot state to {path}: {exc}", file=sys.stderr)


def _parse_route_direct_sites(raw: str | None) -> list[str] | None:
    text = (raw or "").strip()
    if not text:
        return None
    return parse_slovo_ru_direct_routes(text)


def _corp_happ_routing_deeplink(name_mode: str, user_agent: str | None, output_format_mode: str) -> bool:
    if name_mode == NAME_MODE_SLOVO:
        default = "1"
    else:
        default = "0"
    if not _truthy(os.environ.get("CORP_HAPP_ROUTING_DEEPLINK", default)):
        return False
    fmt = resolve_output_format(user_agent, output_format_mode)
    return fmt == FORMAT_HAPP


def _build_response(slot: int, user_agent: str | None) -> CachedResponse:
    master_url = _master_url_for_slot(slot)
    name_mode = os.environ.get("CORP_NAME_MODE", NAME_MODE_BLANC).strip() or NAME_MODE_BLANC
    name_rules = os.environ.get("CORP_NAME_RULES", "").strip()
    output_format_mode = os.environ.get("CORP_OUTPUT_FORMAT_MODE", OUTPUT_FORMAT_AUTO).strip() or OUTPUT_FORMAT_AUTO
    bypass_render_mode = os.environ.get("CORP_BYPASS_RENDER_MODE", BYPASS_RENDER_SOCKS).strip() or BYPASS_RENDER_SOCKS
    route_name = os.environ.get("CORP_ROUTE_NAME", DEFAULT_ROUTE_NAME).strip() or DEFAULT_ROUTE_NAME
    clash_group_name = os.environ.get("CORP_CLASH_GROUP_NAME", DEFAULT_CLASH_GROUP_NAME).strip() or DEFAULT_CLASH_GROUP_NAME
    deactivated = _truthy(os.environ.get(f"CORP_DEACTIVATED_{slot}")) or _truthy(os.environ.get("CORP_DEACTIVATED"))
    happ_routing_deeplink = _corp_happ_routing_deeplink(name_mode, user_agent, output_format_mode)
    happ_routing_direct_sites = _parse_route_direct_sites(os.environ.get("CORP_ROUTE_DIRECT_SITES"))
    slovo_ru_direct_override = _parse_route_direct_sites(os.environ.get("CORP_SLOVO_RU_DIRECT_ROUTES"))

    fmt = resolve_output_format(user_agent, output_format_mode)
    cache_key = (
        slot,
        master_url,
        name_mode,
        name_rules,
        output_format_mode,
        bypass_render_mode,
        fmt,
        route_name,
        clash_group_name,
        deactivated,
        happ_routing_deeplink,
        tuple(happ_routing_direct_sites or ()),
        tuple(slovo_ru_direct_override or ()),
    )
    now = time.time()
    ttl = _cache_ttl()
    with _lock:
        cached = _cache.get(cache_key)
        if cached is not None and now - cached.created_at < ttl:
            return cached

        slot_state: dict[str, Any] = {}
        state_doc: dict[str, Any] | None = None
        if name_mode != NAME_MODE_SLOVO:
            state_doc = _load_state_doc()
            loaded = state_doc.get(str(slot), {})
            slot_state = loaded if isinstance(loaded, dict) else {}

        media_type, content, upstream_headers, next_slot_state = build_subscription_response(
            master_url,
            user_agent,
            deactivated,
            name_mode=name_mode,
            name_rules=name_rules,
            output_format_mode=output_format_mode,
            bypass_render_mode=bypass_render_mode,
            slot_state=slot_state,
            route_name=route_name,
            clash_group_name=clash_group_name,
            slovo_ru_direct_routes_override=slovo_ru_direct_override,
            happ_routing_deeplink=happ_routing_deeplink,
            happ_routing_direct_sites=happ_routing_direct_sites,
        )
        if name_mode != NAME_MODE_SLOVO and state_doc is not None:
            state_doc[str(slot)] = next_slot_state
            _save_state_doc(state_doc)

        response = CachedResponse(
            media_type=media_type,
            body=content.encode("utf-8"),
            headers=_corp_headers(slot, deactivated=deactivated, extra=upstream_headers),
            created_at=now,
        )
        _cache[cache_key] = response
        return response


class CorpVpnHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "CorpVpnProxy/1.0"

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/healthz":
            body = b"OK\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        slot = _slot_from_path(self.path)
        if slot is None:
            self._send_text(404, "Not Found\n")
            return

        try:
            response = _build_response(slot, self.headers.get("User-Agent"))
        except Exception as exc:
            print(f"CORP subscription error for slot {slot}: {exc}", file=sys.stderr)
            self._send_text(502, "Upstream Error\n")
            return

        self.send_response(200)
        self.send_header("Content-Type", response.media_type)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)

    def _send_text(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("CORP_BIND_HOST", DEFAULT_HOST)
    port = int(os.environ.get("CORP_PORT", str(DEFAULT_PORT)))
    server = ThreadingHTTPServer((host, port), CorpVpnHandler)
    print(f"CORP VPN proxy started on {host}:{port}; paths: /CorpVpnSubscription1_..4_")
    server.serve_forever()


if __name__ == "__main__":
    main()
