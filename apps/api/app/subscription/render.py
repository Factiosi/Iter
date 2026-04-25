from __future__ import annotations

import base64
from typing import Any
from urllib.parse import quote, urlencode

import yaml

from app.subscription.nodes import ProxyNode
from app.subscription.ua import FORMAT_FLCLASH, FORMAT_HAPP, FORMAT_THRONE

_CLASH_GROUP_NAME = "Iter VPN"


def _node_to_clash_proxy(n: ProxyNode) -> dict[str, Any]:
    p: dict[str, Any] = {
        "name": n.name,
        "type": "vless",
        "server": n.server,
        "port": n.port,
        "uuid": n.uuid,
        "udp": True,
    }
    if n.flow:
        p["flow"] = n.flow
    if n.network and n.network != "tcp":
        p["network"] = n.network
    if n.tls:
        p["tls"] = True
    if n.sni:
        p["servername"] = n.sni
    if n.network == "ws":
        hdr = {}
        if n.host:
            hdr["Host"] = n.host
        p["ws-opts"] = {"path": n.path or "/", "headers": hdr}
    if n.pbk or n.sid:
        p["reality-opts"] = {
            "public-key": n.pbk or "",
            "short-id": n.sid or "",
        }
        if n.fp:
            p["reality-opts"]["client-fingerprint"] = n.fp
        p["tls"] = True
        p["client-fingerprint"] = n.fp or n.client_fingerprint
    return p


def render_clash_yaml(nodes: list[ProxyNode]) -> str:
    proxies = [_node_to_clash_proxy(n) for n in nodes]
    names = [n["name"] for n in proxies]
    doc = {
        "mixed-port": 7890,
        "mode": "global",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": _CLASH_GROUP_NAME,
                "type": "select",
                "proxies": names,
            }
        ],
        "rules": [f"MATCH,{_CLASH_GROUP_NAME}"],
    }
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=False)


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
    if n.network == "ws":
        if n.path:
            q["path"] = n.path
        if n.host:
            q["host"] = n.host
    tail = urlencode(q)
    frag = quote(n.name, safe="")
    return f"vless://{n.uuid}@{n.server}:{n.port}?{tail}#{frag}"


def render_happ_plain(nodes: list[ProxyNode]) -> str:
    return "\n".join(_node_to_vless_uri(n) for n in nodes) + ("\n" if nodes else "")


def render_uri_bundle_base64(nodes: list[ProxyNode]) -> str:
    """Одна строка base64(UTF-8), как у Throne / типичных Happ-подписок (внутри — URI по строкам)."""
    plain = "\n".join(_node_to_vless_uri(n) for n in nodes)
    return base64.b64encode(plain.encode("utf-8")).decode("ascii")


def render_for_format(fmt: str, nodes: list[ProxyNode]) -> tuple[str, str]:
    """Возвращает (content_type, body)."""
    if fmt == FORMAT_THRONE:
        return "text/plain; charset=utf-8", render_uri_bundle_base64(nodes)
    if fmt == FORMAT_HAPP:
        return "text/plain; charset=utf-8", render_uri_bundle_base64(nodes)
    return "text/yaml; charset=utf-8", render_clash_yaml(nodes)
