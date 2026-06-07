from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import quote, urlencode

import yaml

from app.subscription.nodes import ProxyNode
from app.subscription.ua import FORMAT_FLCLASH, FORMAT_HAPP, FORMAT_THRONE

_CLASH_GROUP_NAME = "Iter VPN"

BYPASS_RENDER_SOCKS = "socks"
BYPASS_RENDER_CHAIN = "chain"
BYPASS_RENDER_BOTH = "both"
VALID_BYPASS_RENDER_MODES = frozenset({BYPASS_RENDER_SOCKS, BYPASS_RENDER_CHAIN, BYPASS_RENDER_BOTH})


def _allow_insecure(extra: dict[str, Any]) -> bool:
    raw = str(extra.get("allowInsecure", "")).strip().lower()
    return raw in {"1", "true", "yes"}


def _resolve_bypass_render_mode(mode: str) -> str:
    return mode if mode in VALID_BYPASS_RENDER_MODES else BYPASS_RENDER_SOCKS


_COUNTRY_BY_ISO2: dict[str, tuple[str, str]] = {
    "ca": ("🇨🇦", "Канада"),
    "ch": ("🇨🇭", "Швейцария"),
    "de": ("🇩🇪", "Германия"),
    "fi": ("🇫🇮", "Финляндия"),
    "fr": ("🇫🇷", "Франция"),
    "gb": ("🇬🇧", "Великобритания"),
    "hk": ("🇭🇰", "Гонконг"),
    "jp": ("🇯🇵", "Япония"),
    "nl": ("🇳🇱", "Нидерланды"),
    "pl": ("🇵🇱", "Польша"),
    "ru": ("🇷🇺", "Россия"),
    "se": ("🇸🇪", "Швеция"),
    "sg": ("🇸🇬", "Сингапур"),
    "tr": ("🇹🇷", "Турция"),
    "us": ("🇺🇸", "США"),
}


_TAG_ISO_PATTERNS = (
    re.compile(r"^([a-z]{2})[-_]"),
    re.compile(r"[-_]([a-z]{2})(?:[-_]|$)"),
    re.compile(r"([a-z]{2})[-_]upstream"),
    re.compile(r"upstream[-_]([a-z]{2})"),
)

_GEO_CACHE: dict[str, tuple[str, str]] = {}


def _country_from_iso2(iso2: str) -> tuple[str, str]:
    return _COUNTRY_BY_ISO2.get(iso2.lower(), ("", iso2.upper()))


def _geo_country_for_ip(ip: str) -> tuple[str, str]:
    if ip in _GEO_CACHE:
        return _GEO_CACHE[ip]
    fallback = ("", "")
    try:
        import httpx

        response = httpx.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,countryCode"},
            timeout=2.5,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "success":
            iso2 = str(payload.get("countryCode") or "").lower()
            if len(iso2) == 2:
                fallback = _country_from_iso2(iso2)
    except Exception:
        pass
    _GEO_CACHE[ip] = fallback
    return fallback


def _transit_country_from_socks(socks: dict[str, Any]) -> tuple[str, str]:
    tag = str(socks.get("tag") or "").lower()
    for pattern in _TAG_ISO_PATTERNS:
        match = pattern.search(tag)
        if match:
            iso2 = match.group(1)
            if iso2 in _COUNTRY_BY_ISO2:
                return _COUNTRY_BY_ISO2[iso2]
    ip = str(socks.get("server") or "").strip()
    if ip:
        return _geo_country_for_ip(ip)
    return ("", "")


_FLAG_PREFIX = re.compile(r"^([\U0001F1E6-\U0001F1FF]{2})\s*")


def _transit_socks_label(socks: dict[str, Any], *, exit_name: str) -> str:
    """🇳🇱 Узел \"Германия Bypass #1\" — флаг транзита + имя exit-сервера в кавычках."""
    transit_flag, _ = _transit_country_from_socks(socks)
    body = _FLAG_PREFIX.sub("", exit_name).lstrip()
    return f'{transit_flag} Узел "{body}"'.strip()


def _singbox_socks_extras() -> dict[str, Any]:
    """UDP-over-TCP: часть SOCKS-транзитов не поддерживает UDP-associate, Telegram может требовать UDP."""
    return {
        "network": "tcp",
        "udp_over_tcp": {"enabled": True, "version": 2},
    }


class _BypassTransitRegistry:
    """Транзитный SOCKS на каждый bypass: флаг транзита + Узел \"{exit}\"."""

    def __init__(self) -> None:
        self._singbox_by_tag: dict[str, dict[str, Any]] = {}
        self._clash_by_tag: dict[str, dict[str, Any]] = {}

    def tag_for(self, socks: dict[str, Any], exit_name: str) -> str:
        return _transit_socks_label(socks, exit_name=exit_name)

    def append_singbox_once(
        self,
        outbounds: list[dict[str, Any]],
        socks: dict[str, Any],
        exit_name: str,
        seen: set[str],
    ) -> str:
        tag = self.tag_for(socks, exit_name)
        if tag not in seen:
            if tag not in self._singbox_by_tag:
                self._singbox_by_tag[tag] = _singbox_socks_outbound(socks, tag)
            outbounds.append(self._singbox_by_tag[tag])
            seen.add(tag)
        return tag

    def append_clash_once(
        self,
        proxies: list[dict[str, Any]],
        socks: dict[str, Any],
        exit_name: str,
        seen: set[str],
    ) -> str:
        tag = self.tag_for(socks, exit_name)
        if tag not in seen:
            if tag not in self._clash_by_tag:
                self._clash_by_tag[tag] = _clash_socks_proxy(socks, tag)
            proxies.append(self._clash_by_tag[tag])
            seen.add(tag)
        return tag


def _singbox_socks_outbound(socks: dict[str, Any], tag: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": "socks",
        "tag": tag,
        "server": str(socks["server"]),
        "server_port": int(socks.get("port") or 1080),
        "version": "5",
        **_singbox_socks_extras(),
    }
    if socks.get("username"):
        out["username"] = str(socks.get("username"))
    if socks.get("password"):
        out["password"] = str(socks.get("password"))
    return out


def _clash_socks_proxy(socks: dict[str, Any], tag: str) -> dict[str, Any]:
    p: dict[str, Any] = {
        "name": tag,
        "type": "socks5",
        "server": str(socks["server"]),
        "port": int(socks.get("port") or 1080),
        "udp": True,
    }
    if socks.get("username"):
        p["username"] = str(socks.get("username"))
    if socks.get("password"):
        p["password"] = str(socks.get("password"))
    return p


def _node_to_clash_proxy(n: ProxyNode, *, dial_tag: str | None = None) -> dict[str, Any]:
    if n.protocol == "hysteria2":
        p: dict[str, Any] = {
            "name": n.name,
            "type": "hysteria2",
            "server": n.server,
            "port": n.port,
            "password": n.password or "",
            "udp": True,
        }
        if n.sni:
            p["sni"] = n.sni
        if n.alpn:
            p["alpn"] = n.alpn
        if n.skip_cert_verify:
            p["skip-cert-verify"] = True
        return p

    p: dict[str, Any] = {
        "name": n.name,
        "type": "vless",
        "server": n.server,
        "port": n.port,
        "uuid": n.uuid,
        "udp": True,
        "encryption": "",
        "packet-encoding": "xudp",
    }
    if n.flow:
        p["flow"] = n.flow

    network = (n.network or "tcp").lower()
    p["network"] = network

    if n.tls or n.pbk or n.sid:
        p["tls"] = True
    if n.sni:
        p["servername"] = n.sni

    fp = n.fp or n.client_fingerprint
    if fp:
        p["client-fingerprint"] = fp
    if _allow_insecure(n.extra):
        p["skip-cert-verify"] = True

    alpn = n.extra.get("alpn")
    if alpn:
        p["alpn"] = [part.strip() for part in str(alpn).split(",") if part.strip()]

    packet_encoding = n.extra.get("packetEncoding") or n.extra.get("packet-encoding")
    if packet_encoding:
        p["packet-encoding"] = str(packet_encoding)

    if network == "ws":
        hdr: dict[str, str] = {}
        if n.host:
            hdr["Host"] = n.host
        p["ws-opts"] = {"path": n.path or "/", "headers": hdr}
    elif network == "xhttp":
        opts: dict[str, Any] = {"path": n.path or "/"}
        if n.host:
            opts["host"] = n.host
        mode = n.extra.get("mode")
        if mode:
            opts["mode"] = str(mode)
        xhttp_extra = n.extra.get("_xhttp_extra")
        if isinstance(xhttp_extra, dict):
            opts.update(_xhttp_extra_to_mihomo(xhttp_extra))
        p["xhttp-opts"] = opts
        p.setdefault("alpn", ["h2"])

    if n.pbk or n.sid:
        p["reality-opts"] = {
            "public-key": n.pbk or "",
            "short-id": n.sid or "",
        }
        if fp:
            p["reality-opts"]["client-fingerprint"] = fp
        p["tls"] = True
    if dial_tag:
        p["dialer-proxy"] = dial_tag
    return p


def _camel_to_kebab(s: str) -> str:
    known = {
        "uplinkHTTPMethod": "uplink-http-method",
        "noGRPCHeader": "no-grpc-header",
        "noSSEHeader": "no-sse-header",
        "scMaxEachPostBytes": "sc-max-each-post-bytes",
        "scMaxConcurrentPosts": "sc-max-concurrent-posts",
        "scMinPostsIntervalMs": "sc-min-posts-interval-ms",
        "scMaxBufferedPosts": "sc-max-buffered-posts",
        "scStreamUpServerSecs": "sc-stream-up-server-secs",
        "xPaddingBytes": "x-padding-bytes",
        "xPaddingKey": "x-padding-key",
        "xPaddingHeader": "x-padding-header",
        "xPaddingMethod": "x-padding-method",
        "xPaddingObfsMode": "x-padding-obfs-mode",
        "xPaddingPlacement": "x-padding-placement",
        "uplinkDataKey": "uplink-data-key",
        "uplinkDataPlacement": "uplink-data-placement",
        "uplinkChunkSize": "uplink-chunk-size",
        "sessionKey": "session-key",
        "sessionPlacement": "session-placement",
        "seqKey": "seq-key",
        "seqPlacement": "seq-placement",
        "hKeepAlivePeriod": "h-keep-alive-period",
        "hMaxReusableSecs": "h-max-reusable-secs",
    }
    if s in known:
        return known[s]
    out = []
    for ch in s:
        if ch.isupper():
            out.append("-")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out).lstrip("-")


def _xhttp_extra_to_mihomo(extra: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in extra.items():
        if key == "xmux" and isinstance(value, dict):
            out["reuse-settings"] = {_camel_to_kebab(str(k)): v for k, v in value.items()}
            continue
        out[_camel_to_kebab(str(key))] = value
    return out


def render_clash_yaml(
    nodes: list[ProxyNode],
    *,
    group_name: str = _CLASH_GROUP_NAME,
    bypass_render_mode: str = BYPASS_RENDER_SOCKS,
) -> str:
    mode = _resolve_bypass_render_mode(bypass_render_mode)
    proxies: list[dict[str, Any]] = []
    transit_registry = _BypassTransitRegistry()
    dial_seen: set[str] = set()
    for n in nodes:
        if n.extra.get("_dialer_socks"):
            socks_cfg = n.extra["_dialer_socks"]
            if mode in {BYPASS_RENDER_CHAIN, BYPASS_RENDER_BOTH}:
                dial_tag = transit_registry.append_clash_once(proxies, socks_cfg, n.name, dial_seen)
                proxies.append(_node_to_clash_proxy(n, dial_tag=dial_tag))
            else:
                transit_registry.append_clash_once(proxies, socks_cfg, n.name, dial_seen)
            continue
        proxies.append(_node_to_clash_proxy(n))
    names: list[str] = []
    for n in nodes:
        if n.extra.get("_dialer_socks"):
            socks_cfg = n.extra["_dialer_socks"]
            names.append(transit_registry.tag_for(socks_cfg, n.name))
            if mode in {BYPASS_RENDER_CHAIN, BYPASS_RENDER_BOTH}:
                names.append(n.name)
        else:
            names.append(n.name)
    doc = {
        "mixed-port": 7890,
        "mode": "global",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": group_name,
                "type": "select",
                "proxies": names,
            }
        ],
        "rules": [f"MATCH,{group_name}"],
    }
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)


def _append_bypass_chain_outbounds(
    outbounds: list[dict[str, Any]],
    n: ProxyNode,
    transit_registry: _BypassTransitRegistry,
    dial_seen: set[str],
) -> None:
    socks_cfg = n.extra.get("_dialer_socks")
    if not isinstance(socks_cfg, dict):
        return
    dial_tag = transit_registry.append_singbox_once(outbounds, socks_cfg, n.name, dial_seen)
    outbounds.append(_node_to_singbox_outbound(n, dial_tag=dial_tag))


def _node_to_singbox_outbound(n: ProxyNode, *, dial_tag: str | None = None) -> dict[str, Any]:
    if n.protocol == "hysteria2":
        out: dict[str, Any] = {
            "type": "hysteria2",
            "tag": n.name,
            "server": n.server,
            "server_port": n.port,
            "password": n.password or "",
            "tls": {"enabled": True},
        }
        if n.sni:
            out["tls"]["server_name"] = n.sni
        if n.alpn:
            out["tls"]["alpn"] = n.alpn
        if n.skip_cert_verify:
            out["tls"]["insecure"] = True
        return out

    out = {
        "type": "vless",
        "tag": n.name,
        "server": n.server,
        "server_port": n.port,
        "uuid": n.uuid,
        "packet_encoding": "xudp",
    }
    if n.flow:
        out["flow"] = n.flow

    network = (n.network or "tcp").lower()
    if network == "ws":
        transport: dict[str, Any] = {"type": "ws", "path": n.path or "/"}
        if n.host:
            transport["headers"] = {"Host": n.host}
        out["transport"] = transport
    elif network == "xhttp":
        transport = {"type": "xhttp", "path": n.path or "/"}
        if n.host:
            transport["host"] = n.host
        mode = n.extra.get("mode")
        if mode:
            transport["mode"] = str(mode)
        out["transport"] = transport

    if n.tls or n.pbk or n.sid:
        tls: dict[str, Any] = {"enabled": True}
        if n.sni:
            tls["server_name"] = n.sni
        fp = n.fp or n.client_fingerprint
        if fp:
            tls["utls"] = {"enabled": True, "fingerprint": fp}
        if n.pbk or n.sid:
            tls["reality"] = {"enabled": True}
            if n.pbk:
                tls["reality"]["public_key"] = n.pbk
            if n.sid:
                tls["reality"]["short_id"] = n.sid
        if _allow_insecure(n.extra):
            tls["insecure"] = True
        alpn = n.extra.get("alpn")
        if alpn:
            tls["alpn"] = [part.strip() for part in str(alpn).split(",") if part.strip()]
        out["tls"] = tls

    if dial_tag:
        out["detour"] = dial_tag
    return out


def render_singbox_outbounds_json(
    nodes: list[ProxyNode],
    *,
    bypass_render_mode: str = BYPASS_RENDER_SOCKS,
) -> str:
    mode = _resolve_bypass_render_mode(bypass_render_mode)
    outbounds: list[dict[str, Any]] = []
    transit_registry = _BypassTransitRegistry()
    dial_seen: set[str] = set()
    for n in nodes:
        if (n.network or "").lower() == "xhttp":
            continue
        if n.extra.get("_dialer_socks"):
            if mode in {BYPASS_RENDER_CHAIN, BYPASS_RENDER_BOTH}:
                _append_bypass_chain_outbounds(outbounds, n, transit_registry, dial_seen)
            else:
                socks_cfg = n.extra["_dialer_socks"]
                transit_registry.append_singbox_once(outbounds, socks_cfg, n.name, dial_seen)
            continue
        outbounds.append(_node_to_singbox_outbound(n))
    return json.dumps(outbounds, ensure_ascii=False, separators=(",", ":"))


def _node_to_vless_uri(n: ProxyNode) -> str:
    q: dict[str, str] = {"encryption": "none"}
    if n.network:
        q["type"] = n.network
    if n.flow:
        q["flow"] = n.flow
    if n.tls:
        if n.pbk:
            q["security"] = "reality"
            if n.pbk:
                q["pbk"] = n.pbk
            if n.sid:
                q["sid"] = n.sid
            if n.sni:
                q["sni"] = n.sni
            if n.fp or n.client_fingerprint:
                q["fp"] = n.fp or n.client_fingerprint or ""
        else:
            q["security"] = "tls"
            if n.sni:
                q["sni"] = n.sni
            if n.fp or n.client_fingerprint:
                q["fp"] = n.fp or n.client_fingerprint or ""
    if n.network == "ws":
        if n.path:
            q["path"] = n.path
        if n.host:
            q["host"] = n.host
    elif n.network == "xhttp":
        if n.path:
            q["path"] = n.path
        if n.host:
            q["host"] = n.host
        mode = n.extra.get("mode")
        if mode:
            q["mode"] = str(mode)
    for key, value in n.extra.items():
        if key.startswith("_"):
            continue
        if value is None or str(value) == "":
            continue
        q.setdefault(key, str(value))
    tail = urlencode(q)
    frag = quote(n.name, safe="")
    return f"vless://{n.uuid}@{n.server}:{n.port}?{tail}#{frag}"


def _node_to_hysteria2_uri(n: ProxyNode) -> str:
    q: dict[str, str] = {}
    if n.sni:
        q["sni"] = n.sni
    if n.alpn:
        q["alpn"] = ",".join(n.alpn)
    if n.skip_cert_verify:
        q["insecure"] = "1"
    tail = urlencode(q)
    frag = quote(n.name, safe="")
    auth = quote(n.password or "", safe="")
    sep = f"?{tail}" if tail else ""
    return f"hysteria2://{auth}@{n.server}:{n.port}{sep}#{frag}"


def _node_to_uri(n: ProxyNode) -> str:
    if n.protocol == "hysteria2":
        return _node_to_hysteria2_uri(n)
    return _node_to_vless_uri(n)


def render_happ_plain(nodes: list[ProxyNode]) -> str:
    return "\n".join(_node_to_uri(n) for n in nodes) + ("\n" if nodes else "")


def render_uri_bundle_base64(nodes: list[ProxyNode]) -> str:
    """Одна строка base64(UTF-8), как у Throne / типичных Happ-подписок (внутри — URI по строкам)."""
    plain = "\n".join(_node_to_uri(n) for n in nodes)
    return base64.b64encode(plain.encode("utf-8")).decode("ascii")


def render_for_format(
    fmt: str,
    nodes: list[ProxyNode],
    *,
    group_name: str = _CLASH_GROUP_NAME,
    bypass_render_mode: str = BYPASS_RENDER_SOCKS,
) -> tuple[str, str]:
    """Возвращает (content_type, body)."""
    if fmt == FORMAT_THRONE:
        return "text/plain; charset=utf-8", render_uri_bundle_base64(nodes)
    if fmt == FORMAT_HAPP:
        return "text/plain; charset=utf-8", render_uri_bundle_base64(nodes)
    return "text/yaml; charset=utf-8", render_clash_yaml(
        nodes, group_name=group_name, bypass_render_mode=bypass_render_mode
    )
