from app.subscription.display_names import normalize_server_names
from app.subscription.nodes import ProxyNode


def _n(name: str, server: str = "example.com") -> ProxyNode:
    return ProxyNode(
        name=name,
        uuid="00000000-0000-0000-0000-000000000001",
        server=server,
        port=443,
    )


def test_extra_germany_duplicate_country_gets_counter():
    nodes = [
        _n("🇩🇪 Берлин, Германия, Extra", "1.1.1.1"),
        _n("🇩🇪 Франкфурт, Германия, Extra", "2.2.2.2"),
    ]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇩🇪 Германия #1"
    assert nodes[1].name == "🇩🇪 Германия #2"


def test_extra_single_no_counter():
    nodes = [_n("🇳🇱 Амстердам, Нидерланды, Extra")]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇳🇱 Нидерланды"


def test_whitelist_germany_counter():
    nodes = [
        _n("🇩🇪 Германия, Extra Whitelist(Yota)", "185.1.1.1"),
        _n("🇩🇪 Германия, Extra Whitelist(Beeline)#2", "185.2.2.2"),
    ]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇩🇪 🏳️ Whitelist, Германия #1"
    assert nodes[1].name == "🇩🇪 🏳️ Whitelist, Германия #2"


def test_hongkong_collapse():
    nodes = [_n("🇭🇰 Гонконг, Гонконг, Extra")]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇭🇰 Гонконг"


def test_custom_name_rules_support_dollar_groups():
    nodes = [_n("DE-01 → Blanc VPN")]
    normalize_server_names(nodes, mode="custom", custom_rules=r"^([A-Z]{2})-\d+.* => $1 custom")
    assert nodes[0].name == "DE custom"
