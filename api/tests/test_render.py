import yaml

from app.subscription.nodes import ProxyNode
from app.subscription.render import _node_to_vless_uri, render_clash_yaml


def test_render_clash_yaml_uses_iter_vpn_group_and_rule():
    nodes = [
        ProxyNode(name="🇩🇪 Германия", uuid="u1", server="example.com", port=443),
        ProxyNode(name="🇳🇱 Нидерланды", uuid="u2", server="example.org", port=8443),
    ]
    rendered = render_clash_yaml(nodes)
    data = yaml.safe_load(rendered)
    assert data["proxy-groups"][0]["name"] == "Iter VPN"
    assert data["rules"] == ["MATCH,Iter VPN"]


def test_vless_uri_explicitly_keeps_tcp_type():
    node = ProxyNode(name="🇩🇪 Германия", uuid="u1", server="example.com", port=443, network="tcp")
    rendered = _node_to_vless_uri(node)
    assert "type=tcp" in rendered
