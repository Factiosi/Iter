import json

import yaml

from app.subscription.display_names import normalize_server_names
from app.subscription.parser import parse_subscription_text
from app.subscription.render import (
    BYPASS_RENDER_BOTH,
    BYPASS_RENDER_CHAIN,
    BYPASS_RENDER_SOCKS,
    render_clash_yaml,
    render_singbox_outbounds_json,
    render_uri_bundle_base64,
)


def _vless_config(
    remarks: str,
    *,
    address: str,
    tag: str = "proxy",
    dialer: bool = False,
    socks_address: str = "45.192.48.93",
):
    outbounds = [
        {
            "tag": tag,
            "protocol": "vless",
            "settings": {
                "vnext": [
                    {
                        "address": address,
                        "port": 8443,
                        "users": [
                            {
                                "id": "00000000-0000-0000-0000-000000000001",
                                "encryption": "none",
                                "flow": "xtls-rprx-vision",
                            }
                        ],
                    }
                ]
            },
            "streamSettings": {
                "network": "tcp",
                "security": "reality",
                "realitySettings": {
                    "fingerprint": "firefox",
                    "publicKey": "public-key",
                    "serverName": "rbc.ru",
                    "shortId": "short-id",
                },
                **({"sockopt": {"dialerProxy": "ru-upstream"}} if dialer else {}),
            },
        },
        {"tag": "direct", "protocol": "freedom"},
        {"tag": "block", "protocol": "blackhole"},
    ]
    if dialer:
        outbounds.insert(
            1,
            {
                "tag": "ru-upstream",
                "protocol": "socks",
                "settings": {
                    "servers": [
                        {
                            "address": socks_address,
                            "port": 62671,
                            "users": [{"user": "u", "pass": "p"}],
                        }
                    ]
                },
            },
        )
    return {"remarks": remarks, "outbounds": outbounds, "routing": {"rules": []}}


def test_liberty_json_parser_keeps_bypass_and_skips_auto_separator():
    body = json.dumps(
        [
            _vless_config("🇪🇺 🚀Авто | Лучший сервер ⚡⚡", address="auto.example"),
            _vless_config("⬇️ Обходы белых списков ⬇️", address="separator.example"),
            _vless_config("🇩🇪⚡Германия", address="de.example"),
            _vless_config("🇩🇪⚡Германия bypass", address="bypass.de.example", dialer=True),
        ],
        ensure_ascii=False,
    )
    nodes = parse_subscription_text(body)
    assert [n.server for n in nodes] == ["de.example", "bypass.de.example"]
    assert nodes[1].extra["_dialer_socks"]["server"] == "45.192.48.93"


def test_liberty_names_mark_bypass_whitelist_and_gaming():
    nodes = parse_subscription_text(
        json.dumps(
            [
                _vless_config("🇨🇭🤩Швейцария-2", address="ch2.example"),
                _vless_config("🇨🇭⚡Швейцария", address="ch.example"),
                _vless_config("🇨🇭⚡Швейцария bypass", address="bypass.ch.example", dialer=True),
                _vless_config("🇨🇭⚪Швейцария (БС-7) ☁️", address="wl.example", tag="proxy-wl-test"),
            ],
            ensure_ascii=False,
        )
    )
    normalize_server_names(nodes, mode="liberty")
    assert nodes[0].name == "🇨🇭 Швейцария #2"
    assert nodes[1].name == "🇨🇭 Швейцария #1"
    assert nodes[2].name == "🇨🇭 Швейцария Bypass"
    assert nodes[3].name == "🇨🇭 🏳️ Whitelist, Швейцария"


def test_liberty_hysteria2_renders_for_uri_and_clash():
    body = json.dumps(
        [
            {
                "remarks": "🇳🇱🎮Нидерланды GAMING",
                "outbounds": [
                    {
                        "tag": "proxy",
                        "protocol": "hysteria",
                        "settings": {"address": "game.example", "port": 9443, "version": 2},
                        "streamSettings": {
                            "network": "hysteria",
                            "security": "tls",
                            "hysteriaSettings": {"auth": "secret", "version": 2},
                            "tlsSettings": {"serverName": "game.example", "alpn": ["h3"]},
                        },
                    }
                ],
            }
        ],
        ensure_ascii=False,
    )
    nodes = parse_subscription_text(body)
    normalize_server_names(nodes, mode="liberty")
    assert nodes[0].name == "🇳🇱 Нидерланды Gaming"
    assert "aHlzdGVyaWEyOi8vc2VjcmV0QGdhbWUuZXhhbXBsZTo5NDQz" in render_uri_bundle_base64(nodes)
    clash = yaml.safe_load(render_clash_yaml(nodes))
    assert clash["proxies"][0]["type"] == "hysteria2"


def test_liberty_flclash_renders_bypass_as_transit_socks_endpoint():
    nodes = parse_subscription_text(
        json.dumps([
            _vless_config(
                "🇩🇪⚡Германия bypass",
                address="bypass.de.example",
                dialer=True,
                socks_address="192.0.2.1",
            )
        ])
    )
    normalize_server_names(nodes, mode="liberty")
    clash = yaml.safe_load(render_clash_yaml(nodes, bypass_render_mode=BYPASS_RENDER_SOCKS))
    assert clash["proxy-groups"][0]["proxies"] == ['🇷🇺 Узел "Германия Bypass"']
    assert clash["proxies"][0]["name"] == '🇷🇺 Узел "Германия Bypass"'
    assert clash["proxies"][0]["type"] == "socks5"


def test_liberty_flclash_renders_bypass_as_chain_when_requested():
    nodes = parse_subscription_text(
        json.dumps([
            _vless_config(
                "🇩🇪⚡Германия bypass",
                address="bypass.de.example",
                dialer=True,
                socks_address="192.0.2.1",
            )
        ])
    )
    normalize_server_names(nodes, mode="liberty")
    clash = yaml.safe_load(render_clash_yaml(nodes, bypass_render_mode=BYPASS_RENDER_CHAIN))
    assert clash["proxy-groups"][0]["proxies"] == [
        '🇷🇺 Узел "Германия Bypass"',
        "🇩🇪 Германия Bypass",
    ]
    assert len(clash["proxies"]) == 2
    assert clash["proxies"][0]["type"] == "socks5"
    assert clash["proxies"][1]["type"] == "vless"
    assert clash["proxies"][0]["name"] == '🇷🇺 Узел "Германия Bypass"'
    assert clash["proxies"][1]["name"] == "🇩🇪 Германия Bypass"
    assert clash["proxies"][1]["dialer-proxy"] == clash["proxies"][0]["name"]


def test_liberty_throne_renders_bypass_as_transit_socks_endpoint():
    nodes = parse_subscription_text(
        json.dumps([
            _vless_config(
                "🇨🇦⚡Канада bypass",
                address="bypass.ca.example",
                dialer=True,
                socks_address="192.0.2.1",
            )
        ])
    )
    normalize_server_names(nodes, mode="liberty")
    outbounds = json.loads(render_singbox_outbounds_json(nodes, bypass_render_mode=BYPASS_RENDER_SOCKS))
    assert outbounds == [
        {
            "type": "socks",
            "tag": '🇷🇺 Узел "Канада Bypass"',
            "server": "192.0.2.1",
            "server_port": 62671,
            "version": "5",
            "network": "tcp",
            "udp_over_tcp": {"enabled": True, "version": 2},
            "username": "u",
            "password": "p",
        }
    ]


def test_liberty_throne_socks_includes_udp_over_tcp():
    nodes = parse_subscription_text(
        json.dumps([
            _vless_config(
                "🇨🇦⚡Канада bypass",
                address="bypass.ca.example",
                dialer=True,
                socks_address="192.0.2.1",
            )
        ])
    )
    normalize_server_names(nodes, mode="liberty")
    outbounds = json.loads(render_singbox_outbounds_json(nodes, bypass_render_mode=BYPASS_RENDER_SOCKS))
    assert outbounds[0]["udp_over_tcp"] == {"enabled": True, "version": 2}


def test_liberty_throne_both_mode_exports_transit_and_bypass():
    nodes = parse_subscription_text(
        json.dumps([
            _vless_config(
                "🇨🇦⚡Канада bypass",
                address="bypass.ca.example",
                dialer=True,
                socks_address="192.0.2.1",
            )
        ])
    )
    normalize_server_names(nodes, mode="liberty")
    outbounds = json.loads(render_singbox_outbounds_json(nodes, bypass_render_mode=BYPASS_RENDER_BOTH))
    assert len(outbounds) == 2
    assert outbounds[0]["type"] == "socks"
    assert outbounds[0]["tag"] == '🇷🇺 Узел "Канада Bypass"'
    assert outbounds[1]["type"] == "vless"
    assert outbounds[1]["tag"] == "🇨🇦 Канада Bypass"
    assert outbounds[1]["detour"] == '🇷🇺 Узел "Канада Bypass"'


def test_liberty_throne_keeps_separate_transit_nodes_per_bypass_exit():
    nodes = parse_subscription_text(
        json.dumps([
            _vless_config(
                "🇩🇪⚡Германия bypass",
                address="bypass.de.example",
                dialer=True,
                socks_address="192.0.2.1",
            ),
            _vless_config(
                "🇨🇦⚡Канада bypass",
                address="bypass.ca.example",
                dialer=True,
                socks_address="192.0.2.1",
            ),
        ])
    )
    normalize_server_names(nodes, mode="liberty")
    outbounds = json.loads(render_singbox_outbounds_json(nodes, bypass_render_mode=BYPASS_RENDER_CHAIN))
    dial_tags = [o["tag"] for o in outbounds if o.get("type") == "socks"]
    assert dial_tags == ['🇷🇺 Узел "Германия Bypass"', '🇷🇺 Узел "Канада Bypass"']
    assert all(
        o.get("detour") in dial_tags
        for o in outbounds
        if o.get("type") == "vless" and o.get("detour")
    )


def test_liberty_throne_renders_bypass_as_chain_when_requested():
    nodes = parse_subscription_text(
        json.dumps([
            _vless_config(
                "🇨🇦⚡Канада bypass",
                address="bypass.ca.example",
                dialer=True,
                socks_address="192.0.2.1",
            )
        ])
    )
    normalize_server_names(nodes, mode="liberty")
    outbounds = json.loads(render_singbox_outbounds_json(nodes, bypass_render_mode=BYPASS_RENDER_CHAIN))
    assert len(outbounds) == 2
    assert outbounds[0]["type"] == "socks"
    assert outbounds[0]["tag"] == '🇷🇺 Узел "Канада Bypass"'
    assert outbounds[1]["type"] == "vless"
    assert outbounds[1]["tag"] == "🇨🇦 Канада Bypass"
    assert outbounds[1]["detour"] == '🇷🇺 Узел "Канада Bypass"'
