from __future__ import annotations

import logging
import json
import base64
from copy import deepcopy

from app.subscription.display_names import NAME_MODE_LIBERTY
from app.subscription.display_names import normalize_server_names
from app.subscription.server_slots import ServerSlotState
from app.subscription.fetch import fetch_master_subscription_sync
from app.subscription.out_headers import build_subscription_headers
from app.subscription.parser import filter_liberty_configs, parse_subscription_text
from app.subscription.poison import apply_poisoning
from app.subscription.render import BYPASS_RENDER_SOCKS
from app.subscription.render import render_for_format
from app.subscription.render import render_singbox_outbounds_json
from app.subscription.ua import FORMAT_HAPP, FORMAT_THRONE, OUTPUT_FORMAT_AUTO, resolve_output_format

logger = logging.getLogger(__name__)


def build_subscription_response(
    master_url: str,
    user_agent: str | None,
    poisoning: bool,
    *,
    name_mode: str = "blanc",
    name_rules: str = "",
    output_format_mode: str = OUTPUT_FORMAT_AUTO,
    bypass_render_mode: str = BYPASS_RENDER_SOCKS,
    slot_state: ServerSlotState | None = None,
    route_name: str = "Iter Route",
    clash_group_name: str = "Iter VPN",
) -> tuple[str, str, dict[str, str], ServerSlotState]:
    """
    Загрузка мастер-подписки (UA фиксирован в fetch) → парсинг → имена или отзыв →
    сериализация по UA клиента + заголовки без лишних полей апстрима.
    """
    _ct, body = fetch_master_subscription_sync(master_url)
    nodes = parse_subscription_text(body)
    if not nodes:
        raise ValueError("Не удалось разобрать подписку (нет узлов VLESS)")

    nodes = deepcopy(nodes)
    fmt = resolve_output_format(user_agent, output_format_mode)
    slots: ServerSlotState = dict(slot_state or {})
    if poisoning:
        nodes = apply_poisoning(nodes)
    else:
        slots = normalize_server_names(
            nodes,
            mode=name_mode,
            custom_rules=name_rules,
            slot_state=slots,
        )
        if name_mode == NAME_MODE_LIBERTY:
            if fmt == FORMAT_HAPP:
                liberty_json = _render_liberty_json_subscription(body, nodes)
                if liberty_json is not None:
                    headers = build_subscription_headers(deactivated=False, fmt=fmt)
                    headers["routing"] = _happ_route_deeplink(route_name)
                    return "application/json; charset=utf-8", liberty_json, headers, slots
            if fmt == FORMAT_THRONE:
                headers = build_subscription_headers(deactivated=False, fmt=fmt)
                return (
                    "application/json; charset=utf-8",
                    render_singbox_outbounds_json(nodes, bypass_render_mode=bypass_render_mode),
                    headers,
                    slots,
                )

    media_type, content = render_for_format(
        fmt, nodes, group_name=clash_group_name, bypass_render_mode=bypass_render_mode
    )
    headers = build_subscription_headers(deactivated=poisoning, fmt=fmt)
    return media_type, content, headers, slots


def _render_liberty_json_subscription(body: str, nodes: list) -> str | None:
    """
    LIBERTY отдаёт полноценные клиентские JSON-конфиги. Для bypass/БС важно сохранить
    routing, balancers, dialerProxy и decoy-узлы, поэтому меняем только список и remarks.
    """
    text = body.strip()
    if not (text.startswith("[") or text.startswith("{")):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    configs = filter_liberty_configs(data)
    if len(configs) != len(nodes):
        logger.warning("LIBERTY config/node count mismatch configs=%s nodes=%s", len(configs), len(nodes))
    out = []
    for config, node in zip(configs, nodes):
        c = deepcopy(config)
        c["remarks"] = node.name
        out.append(c)
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def _happ_route_deeplink(name: str = "Iter Route") -> str:
    route = {
        "blockip": [],
        "blocksites": [],
        "directip": [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "169.254.0.0/16",
            "224.0.0.0/4",
            "255.255.255.255",
        ],
        "directsites": ["domain:.ru", "domain:.xn--p1ai", "geosite:category-ru"],
        "dnshosts": {"cloudflare-dns.com": "1.1.1.1", "dns.google": "8.8.8.8"},
        "domainstrategy": "IPIfNonMatch",
        "domesticdnsdomain": "https://dns.google/dns-query",
        "domesticdnsip": "8.8.8.8",
        "domesticdnstype": "DoH",
        "fakedns": False,
        "geoipurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat",
        "geositeurl": "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat",
        "globalproxy": True,
        "name": name,
        "proxyip": [],
        "proxysites": [],
        "remotednsdomain": "https://cloudflare-dns.com/dns-query",
        "remotednsip": "1.1.1.1",
        "remotednstype": "DoH",
        "routeorder": "block-direct-proxy",
    }
    raw = json.dumps(route, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "happ://routing/add/" + base64.b64encode(raw).decode("ascii")
