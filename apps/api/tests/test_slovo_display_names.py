from app.subscription.display_names import normalize_server_names
from app.subscription.nodes import ProxyNode


def _n(name: str) -> ProxyNode:
    return ProxyNode(
        name=name,
        uuid="00000000-0000-0000-0000-000000000001",
        server="example.com",
        port=443,
    )


def test_slovo_names_without_route_suffix():
    nodes = [
        _n("🇵🇱 Польша · RU сайты работают"),
        _n("🇸🇪 Швеция II · все через VPN"),
    ]
    normalize_server_names(nodes, mode="slovo")
    assert nodes[0].name == "🇵🇱 Польша"
    assert nodes[1].name == "🇸🇪 Швеция #2"
