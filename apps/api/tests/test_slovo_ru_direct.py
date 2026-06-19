import json

import pytest

from app.subscription.slovo_ru_direct import (
    apply_slovo_ru_direct_routes_to_config,
    extract_provider_slovo_ru_direct_domains,
    parse_slovo_ru_direct_routes,
    validate_slovo_ru_direct_routes,
)


def test_parse_and_validate_routes():
    text = """
    domain:2ip.ru
    geosite:category-ru
    # comment
    suffix:.ru
    """
    routes = validate_slovo_ru_direct_routes(text)
    assert routes == ["domain:2ip.ru", "geosite:category-ru", "suffix:.ru"]


def test_validate_rejects_unknown_prefix():
    with pytest.raises(ValueError, match="2ip.ru"):
        validate_slovo_ru_direct_routes("2ip.ru")


def test_extract_provider_routes_from_slovo_json():
    body = json.dumps(
        [
            {
                "remarks": "🇩🇪 Германия · RU сайты работают",
                "routing": {
                    "rules": [
                        {"type": "field", "outboundTag": "proxy"},
                        {
                            "type": "field",
                            "outboundTag": "direct",
                            "domain": ["domain:afisha.ru", "geosite:category-ru"],
                        },
                    ]
                },
            }
        ],
        ensure_ascii=False,
    )
    assert extract_provider_slovo_ru_direct_domains(body) == [
        "domain:afisha.ru",
        "geosite:category-ru",
    ]


def test_apply_replaces_direct_domains_fully():
    config = {
        "remarks": "🇩🇪 Германия [RU Direct]",
        "routing": {
            "rules": [
                {"type": "field", "outboundTag": "direct", "domain": ["domain:old.ru"]},
            ]
        },
    }
    apply_slovo_ru_direct_routes_to_config(config, ["domain:new.ru"])
    direct = next(r for r in config["routing"]["rules"] if r.get("outboundTag") == "direct")
    assert direct["domain"] == ["domain:new.ru"]


def test_apply_skips_all_proxy_profile():
    config = {
        "remarks": "🇸🇪 Швеция #2 [ALL Proxy]",
        "routing": {"rules": [{"outboundTag": "direct", "domain": ["domain:old.ru"]}]},
    }
    apply_slovo_ru_direct_routes_to_config(config, ["domain:new.ru"])
    direct = next(r for r in config["routing"]["rules"] if r.get("outboundTag") == "direct")
    assert direct["domain"] == ["domain:old.ru"]


def test_apply_creates_direct_rule_when_missing():
    config = {"remarks": "🇩🇪 Германия [RU Direct]", "routing": {"rules": []}}
    apply_slovo_ru_direct_routes_to_config(config, parse_slovo_ru_direct_routes("domain:test.ru"))
    assert config["routing"]["rules"] == [
        {"type": "field", "outboundTag": "direct", "domain": ["domain:test.ru"]},
    ]
