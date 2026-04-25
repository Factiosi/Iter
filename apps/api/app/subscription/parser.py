from __future__ import annotations

import base64
import binascii
import logging
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from app.subscription.display_names import _SERVICE_NAME
from app.subscription.nodes import ProxyNode

logger = logging.getLogger(__name__)


def _qs_first(qs: dict[str, list[str]], key: str) -> str | None:
    v = qs.get(key)
    if not v:
        return None
    return v[0]


def node_from_vless_uri(line: str) -> ProxyNode | None:
    u = urlparse(line.strip())
    if u.scheme != "vless":
        return None
    uuid = (u.username or "").strip()
    server = (u.hostname or "").strip()
    if not server or not uuid:
        return None
    port = int(u.port or 443)
    name = unquote(u.fragment or "") if u.fragment else ""
    qs = parse_qs(u.query, keep_blank_values=True)
    network = _qs_first(qs, "type") or "tcp"
    flow = _qs_first(qs, "flow")
    security = (_qs_first(qs, "security") or "").lower()
    sni = _qs_first(qs, "sni")
    host = _qs_first(qs, "host")
    path = _qs_first(qs, "path")
    fp = _qs_first(qs, "fp")
    pbk = _qs_first(qs, "pbk")
    sid = _qs_first(qs, "sid")
    tls = security in ("tls", "reality")
    return ProxyNode(
        name=name,
        uuid=uuid,
        server=server,
        port=port,
        network=network,
        tls=tls,
        sni=sni,
        host=host,
        path=path,
        client_fingerprint=fp,
        pbk=pbk,
        sid=sid,
        fp=fp,
        flow=flow,
        extra={k: v[0] for k, v in qs.items() if k not in {
            "type", "flow", "security", "sni", "host", "path", "fp", "pbk", "sid",
        }},
    )


def node_from_clash_proxy(p: dict[str, Any]) -> ProxyNode | None:
    if (p.get("type") or "").lower() != "vless":
        return None
    name = str(p.get("name") or "")
    server = str(p.get("server") or "")
    uuid = str(p.get("uuid") or "")
    if not server or not uuid:
        return None
    port = int(p.get("port") or 443)
    network = str(p.get("network") or "tcp")
    tls = bool(p.get("tls"))
    sni = p.get("servername") or p.get("sni")
    flow = p.get("flow")
    path = None
    host = None
    if network == "ws":
        ws = p.get("ws-opts") or {}
        path = ws.get("path")
        hdr = ws.get("headers") or {}
        if isinstance(hdr, dict):
            host = hdr.get("Host")
    pbk = sid = fp = None
    reality = p.get("reality-opts") or {}
    if reality:
        pbk = reality.get("public-key")
        sid = reality.get("short-id")
        fp = reality.get("client-fingerprint") or p.get("client-fingerprint")
    return ProxyNode(
        name=name,
        uuid=uuid,
        server=server,
        port=port,
        network=network,
        tls=tls,
        sni=str(sni) if sni else None,
        host=str(host) if host else None,
        path=str(path) if path else None,
        client_fingerprint=str(fp) if fp else None,
        pbk=str(pbk) if pbk else None,
        sid=str(sid) if sid else None,
        fp=str(fp) if fp else None,
        flow=str(flow) if flow else None,
        extra={},
    )


def _filter_service_nodes(nodes: list[ProxyNode]) -> list[ProxyNode]:
    out: list[ProxyNode] = []
    for n in nodes:
        if _SERVICE_NAME.search(n.name.strip()):
            continue
        if "blanc vpn" in n.name.lower() and "→" in n.name:
            continue
        out.append(n)
    return out


def parse_subscription_text(body: str) -> list[ProxyNode]:
    text = body.strip()
    if not text:
        return []

    # YAML Clash
    if text.startswith("proxies:") or "\nproxies:" in text or text.startswith("mixed-port:"):
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                proxies = data.get("proxies") or []
                nodes: list[ProxyNode] = []
                for p in proxies:
                    if not isinstance(p, dict):
                        continue
                    n = node_from_clash_proxy(p)
                    if n:
                        nodes.append(n)
                return _filter_service_nodes(nodes)
        except yaml.YAMLError:
            logger.debug("YAML parse failed, trying other formats")

    # Base64 (подписка одной строкой)
    if "://" not in text[:200] and not text.startswith("vless:"):
        try:
            pad = (-len(text)) % 4
            dec = base64.b64decode(text + ("=" * pad), validate=False).decode("utf-8", errors="ignore")
            if "vless://" in dec:
                text = dec
        except (binascii.Error, ValueError):
            pass

    nodes = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vless://"):
            n = node_from_vless_uri(line)
            if n:
                nodes.append(n)
    return _filter_service_nodes(nodes)
