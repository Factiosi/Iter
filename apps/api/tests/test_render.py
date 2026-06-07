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


def test_clash_proxy_preserves_ws_tls_fp_skip_cert_and_packet_encoding():
    node = ProxyNode(
        name="Whitelist#1",
        uuid="u1",
        server="185.242.19.9",
        port=443,
        network="ws",
        tls=True,
        sni="top.example.com",
        host="cdn.example.com",
        path="/api/v1/chat/x",
        fp="chrome",
        extra={"allowInsecure": "1", "packetEncoding": "xudp"},
    )
    from app.subscription.render import _node_to_clash_proxy

    proxy = _node_to_clash_proxy(node)
    assert proxy["network"] == "ws"
    assert proxy["tls"] is True
    assert proxy["servername"] == "top.example.com"
    assert proxy["client-fingerprint"] == "chrome"
    assert proxy["skip-cert-verify"] is True
    assert proxy["packet-encoding"] == "xudp"
    assert proxy["ws-opts"]["headers"]["Host"] == "cdn.example.com"


def test_vless_uri_preserves_ws_tls_fp_and_allow_insecure():
    node = ProxyNode(
        name="Whitelist#1",
        uuid="u1",
        server="185.242.19.249",
        port=443,
        network="ws",
        tls=True,
        sni="top.example.com",
        host="cdn.example.com",
        path="/api/v1/chat/conversations/x",
        fp="chrome",
        extra={"allowInsecure": "1"},
    )
    rendered = _node_to_vless_uri(node)
    assert "fp=chrome" in rendered
    assert "allowInsecure=1" in rendered
    assert "type=ws" in rendered
