from app.routers.vpn_routes import _main_payload
from app.subscription.out_headers import build_subscription_headers
from app.subscription.poison import apply_poisoning
from app.subscription.ua import FORMAT_FLCLASH, FORMAT_HAPP
from app.subscription.nodes import ProxyNode


def test_main_payload_uses_config_url_for_happ_and_flclash():
    payload = _main_payload("slug123", "user-local")
    assert payload.happ_url == "happ://add/https://iter.factiosi.com/config/slug123"
    assert payload.flclash_url == "clash://install-config?url=https://iter.factiosi.com/config/slug123"
    assert payload.config_text == "https://iter.factiosi.com/config/slug123"


def test_active_profile_title_matches_iter_vpn():
    headers = build_subscription_headers(deactivated=False, fmt=FORMAT_HAPP)
    assert headers["profile-title"] == "base64:SXRlciBWUE4="


def test_deactivated_profile_title_is_set():
    headers = build_subscription_headers(deactivated=True, fmt=FORMAT_FLCLASH)
    assert headers["profile-title"].startswith("base64:")


def test_poisoning_sets_broken_uuid_port_and_name():
    nodes = [
        ProxyNode(name="🇩🇪 Германия", uuid="u1", server="example.com", port=443),
        ProxyNode(name="🇫🇷 Франция", uuid="u2", server="example.org", port=8443),
    ]
    poisoned = apply_poisoning(nodes)
    assert all(n.port == 666 for n in poisoned)
    assert all(n.uuid == "66666666-6666-6666-6666-666666666666" for n in poisoned)
    assert poisoned[0].name == "Не доступен #1"
    assert poisoned[1].name == "Не доступен #2"
