import base64
import json
from unittest.mock import patch

import yaml

from app.subscription.display_names import normalize_server_names
from app.subscription.parser import parse_subscription_text
from app.subscription.pipeline import _render_xray_json_subscription, build_subscription_response
from app.subscription.parser import filter_slovo_configs
from app.subscription.render import render_clash_yaml


def _slovo_vless_config(
    remarks: str,
    *,
    address: str,
    network: str = "tcp",
    encryption: str = "none",
    reality: bool = True,
    routing: bool = True,
):
    stream: dict = {"network": network}
    if reality and network == "tcp":
        stream["security"] = "reality"
        stream["realitySettings"] = {
            "fingerprint": "edge",
            "publicKey": "public-key",
            "serverName": "www.intel.com",
            "shortId": "short-id",
        }
    elif network == "xhttp" and reality:
        stream["security"] = "reality"
        stream["realitySettings"] = {
            "fingerprint": "edge",
            "publicKey": "public-key",
            "serverName": "www.intel.com",
            "shortId": "short-id",
        }
    config = {
        "remarks": remarks,
        "outbounds": [
            {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": address,
                            "port": 443,
                            "users": [{"id": "00000000-0000-0000-0000-000000000001", "encryption": encryption}],
                        }
                    ]
                },
                "streamSettings": stream,
            }
        ],
    }
    if routing:
        config["routing"] = {"rules": [{"type": "field", "outboundTag": "proxy"}]}
    return config


def test_slovo_parser_skips_autopick():
    body = json.dumps(
        [
            _slovo_vless_config("🌍 Автовыбор страны", address="auto.example"),
            _slovo_vless_config("🇪🇪 Эстония I · RU сайты работают", address="ee.example"),
            _slovo_vless_config("🇷🇺 Обход белых списков", address="wl1.example"),
        ],
        ensure_ascii=False,
    )
    nodes = parse_subscription_text(body)
    assert [n.server for n in nodes] == ["ee.example", "wl1.example"]


def test_slovo_names_and_whitelist():
    body = json.dumps(
        [
            _slovo_vless_config("🇪🇪 Эстония I · RU сайты работают", address="ee.example"),
            _slovo_vless_config("🇸🇪 Швеция II · все через VPN", address="se2.example", network="xhttp"),
            _slovo_vless_config("🇳🇱 Нидерланды · RU сайты работают", address="nl.example", network="xhttp", reality=False),
            _slovo_vless_config("🇷🇺 Обход белых списков", address="wl1.example"),
            _slovo_vless_config("🇷🇺 Обход белых II", address="wl2.example"),
            _slovo_vless_config("🇷🇺 Обход белых III", address="wl3.example"),
        ],
        ensure_ascii=False,
    )
    nodes = parse_subscription_text(body)
    normalize_server_names(nodes, mode="slovo")
    assert nodes[0].name == "🇪🇪 Эстония #1"
    assert nodes[1].name == "🇸🇪 Швеция #2"
    assert nodes[2].name == "🇳🇱 Нидерланды"
    assert nodes[3].name == "🇷🇺 🏳️ Whitelist #1"
    assert nodes[4].name == "🇷🇺 🏳️ Whitelist #2"
    assert nodes[5].name == "🇷🇺 🏳️ Whitelist #3"


def test_slovo_names_ignore_slot_state():
    nodes = parse_subscription_text(
        json.dumps(
            [_slovo_vless_config("🇩🇪 Германия · RU сайты работают", address="de.example")],
            ensure_ascii=False,
        )
    )
    stale_slots = {"🇩🇪 Германия": {"de.example:443": 1}}
    normalize_server_names(nodes, mode="slovo", slot_state=stale_slots)
    assert nodes[0].name == "🇩🇪 Германия"


def test_slovo_happ_uses_iter_route_deeplink_and_strips_node_routing():
    de = _slovo_vless_config("🇩🇪 Германия · RU сайты работают", address="de.example")
    de["routing"]["rules"].append(
        {"type": "field", "outboundTag": "direct", "domain": ["domain:afisha.ru"]},
    )
    body = json.dumps(
        [
            _slovo_vless_config("🌍 Автовыбор страны", address="auto.example"),
            de,
        ],
        ensure_ascii=False,
    )

    with patch("app.subscription.pipeline.fetch_master_subscription_sync", return_value=("application/json", body)):
        _media, content, headers, _slots = build_subscription_response(
            "https://sub.example/test",
            "Happ/1.0",
            poisoning=False,
            name_mode="slovo",
            slovo_ru_direct_routes_override=["domain:2ip.ru", "domain:afisha.ru"],
        )

    data = json.loads(content)
    assert len(data) == 1
    assert data[0]["remarks"] == "🇩🇪 Германия"
    assert "routing" not in data[0]
    assert headers["routing"].startswith("happ://routing/add/")
    route_b64 = headers["routing"].removeprefix("happ://routing/add/")
    route = json.loads(base64.b64decode(route_b64).decode())
    assert route["name"] == "Iter Route"
    assert route["directsites"] == ["domain:2ip.ru", "domain:afisha.ru"]


def test_slovo_happ_default_direct_sites_without_override():
    config = _slovo_vless_config("🇸🇪 Швеция II · все через VPN", address="se.example", network="xhttp")
    config["routing"]["rules"].append(
        {"type": "field", "outboundTag": "direct", "domain": ["domain:afisha.ru"]},
    )
    body = json.dumps([config], ensure_ascii=False)

    with patch("app.subscription.pipeline.fetch_master_subscription_sync", return_value=("application/json", body)):
        _media, content, headers, _slots = build_subscription_response(
            "https://sub.example/test",
            "Happ/1.0",
            poisoning=False,
            name_mode="slovo",
        )

    data = json.loads(content)
    assert "routing" not in data[0]
    route_b64 = headers["routing"].removeprefix("happ://routing/add/")
    route = json.loads(base64.b64decode(route_b64).decode())
    assert route["directsites"] == ["domain:.ru", "domain:.xn--p1ai", "geosite:category-ru"]


def test_slovo_throne_names_without_route_suffix():
    body = json.dumps(
        [
            _slovo_vless_config("🇪🇪 Эстония I · RU сайты работают", address="ee.example"),
            _slovo_vless_config("🇸🇪 Швеция II · все через VPN", address="se.example", network="xhttp"),
        ],
        ensure_ascii=False,
    )

    with patch("app.subscription.pipeline.fetch_master_subscription_sync", return_value=("application/json", body)):
        _media, content, _headers, _slots = build_subscription_response(
            "https://sub.example/test",
            "Throne/1.0",
            poisoning=False,
            name_mode="slovo",
        )

    import base64
    from urllib.parse import unquote

    plain = base64.b64decode(content).decode()
    names = [unquote(line.split("#", 1)[1]) for line in plain.splitlines() if "#" in line]
    assert names == ["🇪🇪 Эстония #1", "🇸🇪 Швеция #2"]


def test_slovo_flclash_names_without_route_suffix():
    body = json.dumps(
        [
            _slovo_vless_config("🇩🇪 Германия · RU сайты работают", address="de.example"),
        ],
        ensure_ascii=False,
    )

    with patch("app.subscription.pipeline.fetch_master_subscription_sync", return_value=("application/json", body)):
        _media, content, _headers, _slots = build_subscription_response(
            "https://sub.example/test",
            "FlClash/0.1",
            poisoning=False,
            name_mode="slovo",
        )

    data = yaml.safe_load(content)
    assert data["proxies"][0]["name"] == "🇩🇪 Германия"


def test_slovo_throne_gets_share_links_with_mlkem():
    body = json.dumps(
        [
            _slovo_vless_config(
                "🇪🇪 Эстония I · RU сайты работают",
                address="ee.example",
                encryption="mlkem768x25519plus.native.0rtt.test",
            ),
            _slovo_vless_config("🇸🇪 Швеция II · все через VPN", address="se.example", network="xhttp"),
        ],
        ensure_ascii=False,
    )

    with patch("app.subscription.pipeline.fetch_master_subscription_sync", return_value=("application/json", body)):
        media, content, headers, _slots = build_subscription_response(
            "https://sub.example/test",
            "Throne/1.0",
            poisoning=False,
            name_mode="slovo",
        )

    assert media.startswith("text/plain")
    import base64

    plain = base64.b64decode(content).decode()
    lines = [line for line in plain.splitlines() if line.strip()]
    assert len(lines) == 2
    assert "mlkem768x25519plus.native.0rtt.test" in lines[0]
    assert "type=xhttp" in lines[1]
    assert "routing" not in headers


def test_slovo_happ_deeplink_mode_strips_node_routing_and_adds_header():
    de = _slovo_vless_config("🇩🇪 Германия · RU сайты работают", address="de.example")
    de["routing"]["rules"].append(
        {"type": "field", "outboundTag": "direct", "domain": ["domain:afisha.ru"]},
    )
    body = json.dumps([de], ensure_ascii=False)

    with patch("app.subscription.pipeline.fetch_master_subscription_sync", return_value=("application/json", body)):
        _media, content, headers, _slots = build_subscription_response(
            "https://sub.example/test",
            "Happ/1.0",
            poisoning=False,
            name_mode="slovo",
            route_name="CORP Route",
            happ_routing_direct_sites=["domain:2ip.ru", "geosite:category-ru"],
        )

    data = json.loads(content)
    assert "routing" not in data[0]
    assert headers["routing"].startswith("happ://routing/add/")
    route_b64 = headers["routing"].removeprefix("happ://routing/add/")
    route = json.loads(base64.b64decode(route_b64).decode())
    assert route["name"] == "CORP Route"
    assert route["directsites"] == ["domain:2ip.ru", "geosite:category-ru"]


def test_slovo_flclash_still_uses_clash_yaml():
    body = json.dumps(
        [
            _slovo_vless_config(
                "🇪🇪 Эстония I · RU сайты работают",
                address="ee.example",
                encryption="mlkem768x25519plus.native.0rtt.test",
            ),
        ],
        ensure_ascii=False,
    )
    nodes = parse_subscription_text(body)
    normalize_server_names(nodes, mode="slovo")
    yaml_text = render_clash_yaml(nodes)
    data = yaml.safe_load(yaml_text)
    assert data["proxies"][0]["name"] == "🇪🇪 Эстония #1"
    assert data["proxies"][0]["encryption"].startswith("mlkem768")
