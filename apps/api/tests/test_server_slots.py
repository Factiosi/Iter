from app.subscription.display_names import normalize_server_names
from app.subscription.nodes import ProxyNode
from app.subscription.server_slots import assign_group_slots


def _node(name: str, server: str, port: int = 443) -> ProxyNode:
    return ProxyNode(
        name=name,
        uuid="00000000-0000-0000-0000-000000000001",
        server=server,
        port=port,
    )


def test_assign_group_slots_reuses_freed_numbers():
    prev = {"1.1.1.1:443": 1, "2.2.2.2:443": 2, "3.3.3.3:443": 3}
    result = assign_group_slots(prev, ["3.3.3.3:443", "5.5.5.5:443", "12.12.12.12:443"])
    assert result == {
        "3.3.3.3:443": 3,
        "5.5.5.5:443": 1,
        "12.12.12.12:443": 2,
    }


def test_same_host_whitelist_gets_distinct_numbers():
    nodes = [
        _node("🇩🇪 Германия, Extra Whitelist(Yota)#1", "185.242.19.249"),
        _node("🇩🇪 Германия, Extra Whitelist(Beeline)#2", "185.242.19.249"),
        _node("🇩🇪 Германия, Extra Whitelist(MTS)#3", "185.242.19.249"),
    ]
    normalize_server_names(nodes)
    slots = {n.name for n in nodes}
    assert len(slots) == 3
    assert any("#1" in n for n in slots)
    assert any("#2" in n for n in slots)
    assert any("#3" in n for n in slots)


def test_same_whitelist_number_different_carriers_get_distinct_slots():
    """У Blanc бывает Whitelist#3 у Yota и Whitelist#3 у Beeline на одном IP."""
    nodes = [
        _node("🇩🇪 Германия, Extra Whitelist(Yota)#3", "185.242.19.9"),
        _node("🇩🇪 Германия, Extra Whitelist(Beeline)#3", "185.242.19.9"),
    ]
    normalize_server_names(nodes)
    assert nodes[0].name != nodes[1].name
    n0 = int(nodes[0].name.rsplit("#", 1)[-1])
    n1 = int(nodes[1].name.rsplit("#", 1)[-1])
    assert n0 != n1


def test_normalize_server_names_keeps_slot_after_rotation():
    state: dict = {}
    nodes_a = [
        _node("🇩🇪 Берлин, Германия, Extra", "1.1.1.1"),
        _node("🇩🇪 Франкфурт, Германия, Extra", "2.2.2.2"),
        _node("🇩🇪 Гамбург, Германия, Extra", "3.3.3.3"),
    ]
    state = normalize_server_names(nodes_a, slot_state=state)
    assert nodes_a[0].name == "🇩🇪 Германия #1"
    assert nodes_a[1].name == "🇩🇪 Германия #2"
    assert nodes_a[2].name == "🇩🇪 Германия #3"

    nodes_b = [_node("🇩🇪 Гамбург, Германия, Extra", "3.3.3.3")]
    state = normalize_server_names(nodes_b, slot_state=state)
    assert nodes_b[0].name == "🇩🇪 Германия #3"

    nodes_c = [
        _node("🇩🇪 Гамбург, Германия, Extra", "3.3.3.3"),
        _node("🇩🇪 Дрезден, Германия, Extra", "5.5.5.5"),
        _node("🇩🇪 Кёльн, Германия, Extra", "12.12.12.12"),
    ]
    state = normalize_server_names(nodes_c, slot_state=state)
    assert nodes_c[0].name == "🇩🇪 Германия #3"
    assert nodes_c[1].name == "🇩🇪 Германия #1"
    assert nodes_c[2].name == "🇩🇪 Германия #2"
