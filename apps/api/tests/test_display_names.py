from app.subscription.display_names import normalize_server_names
from app.subscription.nodes import ProxyNode


def _n(name: str) -> ProxyNode:
    return ProxyNode(name=name, uuid="00000000-0000-0000-0000-000000000001", server="example.com", port=443)


def test_extra_germany_duplicate_country_gets_counter():
    nodes = [_n("🇩🇪 Берлин, Германия, Extra"), _n("🇩🇪 Франкфурт, Германия, Extra")]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇩🇪 Германия #1"
    assert nodes[1].name == "🇩🇪 Германия #2"


def test_extra_single_no_counter():
    nodes = [_n("🇳🇱 Амстердам, Нидерланды, Extra")]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇳🇱 Нидерланды"


def test_whitelist_germany_counter():
    nodes = [
        _n("🇩🇪 Германия, Extra Whitelist(Yota)"),
        _n("🇩🇪 Германия, Extra Whitelist(Beeline)#2"),
    ]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇩🇪 🏳️ Whitelist, Германия #1"
    assert nodes[1].name == "🇩🇪 🏳️ Whitelist, Германия #2"


def test_hongkong_collapse():
    nodes = [_n("🇭🇰 Гонконг, Гонконг, Extra")]
    normalize_server_names(nodes)
    assert nodes[0].name == "🇭🇰 Гонконг"
