from __future__ import annotations

import logging
from copy import deepcopy

from app.subscription.display_names import normalize_server_names
from app.subscription.fetch import fetch_master_subscription_sync
from app.subscription.out_headers import build_subscription_headers
from app.subscription.parser import parse_subscription_text
from app.subscription.poison import apply_poisoning
from app.subscription.render import render_for_format
from app.subscription.ua import detect_subscription_format

logger = logging.getLogger(__name__)


def build_subscription_response(
    master_url: str,
    user_agent: str | None,
    poisoning: bool,
) -> tuple[str, str, dict[str, str]]:
    """
    Загрузка мастер-подписки (UA фиксирован в fetch) → парсинг → имена или отзыв →
    сериализация по UA клиента + заголовки без лишних полей апстрима.
    """
    _ct, body = fetch_master_subscription_sync(master_url)
    nodes = parse_subscription_text(body)
    if not nodes:
        raise ValueError("Не удалось разобрать подписку (нет узлов VLESS)")

    nodes = deepcopy(nodes)
    fmt = detect_subscription_format(user_agent)
    if poisoning:
        nodes = apply_poisoning(nodes)
    else:
        normalize_server_names(nodes)

    media_type, content = render_for_format(fmt, nodes)
    headers = build_subscription_headers(deactivated=poisoning, fmt=fmt)
    return media_type, content, headers
