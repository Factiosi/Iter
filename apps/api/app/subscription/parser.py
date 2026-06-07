from __future__ import annotations

import base64
import binascii
import json
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


def _protocol(outbound: dict[str, Any]) -> str:
    return str(outbound.get("protocol") or outbound.get("type") or "").lower()


def _first_vless_vnext(outbound: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    settings = outbound.get("settings") or {}
    vnext = settings.get("vnext") or []
    if not isinstance(vnext, list) or not vnext:
        return None
    first = vnext[0]
    if not isinstance(first, dict):
        return None
    users = first.get("users") or []
    user = users[0] if isinstance(users, list) and users and isinstance(users[0], dict) else {}
    return first, user


def _liberty_socks_by_tag(outbounds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    socks: dict[str, dict[str, Any]] = {}
    for outbound in outbounds:
        if _protocol(outbound) != "socks":
            continue
        settings = outbound.get("settings") or {}
        servers = settings.get("servers") or []
        if not isinstance(servers, list) or not servers or not isinstance(servers[0], dict):
            continue
        server = servers[0]
        users = server.get("users") or []
        user = users[0] if isinstance(users, list) and users and isinstance(users[0], dict) else {}
        tag = str(outbound.get("tag") or "")
        if tag:
            socks[tag] = {
                "tag": tag,
                "server": str(server.get("address") or ""),
                "port": int(server.get("port") or 1080),
                "username": str(user.get("user") or ""),
                "password": str(user.get("pass") or ""),
            }
    return socks


def _liberty_vless_node(name: str, outbound: dict[str, Any], socks_by_tag: dict[str, dict[str, Any]]) -> ProxyNode | None:
    parsed = _first_vless_vnext(outbound)
    if parsed is None:
        return None
    first, user = parsed
    server = str(first.get("address") or "").strip()
    uuid = str(user.get("id") or "").strip()
    if not server or not uuid:
        return None

    stream = outbound.get("streamSettings") or {}
    network = str(stream.get("network") or "tcp")
    security = str(stream.get("security") or "").lower()
    reality = stream.get("realitySettings") or {}
    tls_settings = stream.get("tlsSettings") or {}
    ws = stream.get("wsSettings") or {}
    xhttp = stream.get("xhttpSettings") or {}
    extra: dict[str, Any] = {}

    sni = reality.get("serverName") or tls_settings.get("serverName")
    fp = reality.get("fingerprint")
    pbk = reality.get("publicKey")
    sid = reality.get("shortId")
    allow_insecure = reality.get("allowInsecure", tls_settings.get("allowInsecure"))
    if allow_insecure is not None:
        extra["allowInsecure"] = "1" if bool(allow_insecure) else "0"
    alpn = tls_settings.get("alpn")
    if isinstance(alpn, list) and alpn:
        extra["alpn"] = ",".join(str(part) for part in alpn if part)

    host = None
    path = None
    if network == "ws":
        path = ws.get("path")
        headers = ws.get("headers") or {}
        if isinstance(headers, dict):
            host = headers.get("Host")
    elif network == "xhttp":
        path = xhttp.get("path")
        host = xhttp.get("host")
        mode = xhttp.get("mode")
        if mode:
            extra["mode"] = str(mode)
        xhttp_extra = xhttp.get("extra")
        if isinstance(xhttp_extra, dict):
            extra["_xhttp_extra"] = xhttp_extra

    dialer_tag = ((stream.get("sockopt") or {}).get("dialerProxy") or "").strip()
    if dialer_tag and dialer_tag in socks_by_tag:
        extra["_dialer_proxy"] = dialer_tag
        extra["_dialer_socks"] = socks_by_tag[dialer_tag]

    return ProxyNode(
        name=name,
        uuid=uuid,
        server=server,
        port=int(first.get("port") or 443),
        protocol="vless",
        network=network,
        tls=security in ("tls", "reality"),
        sni=str(sni) if sni else None,
        host=str(host) if host else None,
        path=str(path) if path else None,
        client_fingerprint=str(fp) if fp else None,
        pbk=str(pbk) if pbk else None,
        sid=str(sid) if sid else None,
        fp=str(fp) if fp else None,
        flow=str(user.get("flow") or "") or None,
        extra=extra,
    )


def _liberty_hysteria2_node(name: str, outbound: dict[str, Any]) -> ProxyNode | None:
    settings = outbound.get("settings") or {}
    stream = outbound.get("streamSettings") or {}
    hysteria = stream.get("hysteriaSettings") or {}
    tls_settings = stream.get("tlsSettings") or {}
    server = str(settings.get("address") or "").strip()
    if not server:
        return None
    password = str(hysteria.get("auth") or settings.get("auth") or "").strip()
    alpn = tls_settings.get("alpn")
    return ProxyNode(
        name=name,
        uuid="",
        server=server,
        port=int(settings.get("port") or 443),
        protocol="hysteria2",
        network="hysteria2",
        tls=True,
        sni=str(tls_settings.get("serverName") or server),
        password=password,
        alpn=[str(part) for part in alpn] if isinstance(alpn, list) else None,
        skip_cert_verify=bool(tls_settings.get("allowInsecure")),
    )


def _liberty_pick_outbound(config: dict[str, Any], outbounds: list[dict[str, Any]]) -> dict[str, Any] | None:
    remarks = str(config.get("remarks") or "")
    lower = remarks.lower()
    vless = [o for o in outbounds if _protocol(o) == "vless"]
    if "бс" in lower:
        wl = [o for o in vless if str(o.get("tag") or "").startswith("proxy-wl-")]
        if wl:
            return wl[0]
    balancers = (config.get("routing") or {}).get("balancers") or []
    if isinstance(balancers, list):
        for balancer in balancers:
            fallback = str((balancer or {}).get("fallbackTag") or "")
            if fallback:
                match = next((o for o in vless if str(o.get("tag") or "") == fallback), None)
                if match:
                    return match
    match = next((o for o in vless if str(o.get("tag") or "") == "proxy"), None)
    return match or (vless[0] if vless else None)


def is_liberty_separator_or_auto(remarks: str) -> bool:
    lower = remarks.lower()
    if "обходы белых спис" in lower:
        return True
    return "авто" in lower and "лучший сервер" in lower


def filter_liberty_configs(data: Any) -> list[dict[str, Any]]:
    configs = data if isinstance(data, list) else [data]
    return [
        config
        for config in configs
        if isinstance(config, dict)
        and str(config.get("remarks") or "").strip()
        and not is_liberty_separator_or_auto(str(config.get("remarks") or ""))
    ]


def nodes_from_liberty_json(data: Any) -> list[ProxyNode]:
    nodes: list[ProxyNode] = []
    for config in filter_liberty_configs(data):
        remarks = str(config.get("remarks") or "").strip()
        raw_outbounds = config.get("outbounds") or []
        if not isinstance(raw_outbounds, list):
            continue
        outbounds = [o for o in raw_outbounds if isinstance(o, dict)]
        hysteria = next((o for o in outbounds if _protocol(o) == "hysteria"), None)
        if hysteria is not None:
            node = _liberty_hysteria2_node(remarks, hysteria)
            if node:
                nodes.append(node)
            continue
        picked = _liberty_pick_outbound(config, outbounds)
        if picked is None:
            continue
        node = _liberty_vless_node(remarks, picked, _liberty_socks_by_tag(outbounds))
        if node:
            nodes.append(node)
    return nodes


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

    # LIBERTY отдаёт список готовых JSON-конфигов Xray: берём нужные outbounds.
    if text.startswith("[") or text.startswith("{"):
        try:
            data = json.loads(text)
            nodes = nodes_from_liberty_json(data)
            if nodes:
                return nodes
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.debug("JSON parse failed, trying other formats")

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
