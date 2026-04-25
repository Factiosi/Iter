from __future__ import annotations

import base64
from urllib.parse import quote

_ACTIVE_TITLE = "Iter VPN"
_DEACTIVATED_TITLE = "Подписка деактивирована"
_ACTIVE_FILENAME = "Iter VPN"
_DEACTIVATED_FILENAME = "Подписка деактивирована"
_DEACTIVATED_FILENAME_FALLBACK = "subscription-deactivated"


def _content_disposition_filename(filename: str) -> str:
    try:
        filename.encode("latin-1")
    except UnicodeEncodeError:
        fallback = _DEACTIVATED_FILENAME_FALLBACK
        encoded = quote(filename.encode("utf-8"))
        return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'
    return f'attachment; filename="{filename}"'


def build_subscription_headers(*, deactivated: bool, fmt: str) -> dict[str, str]:
    """
    Только заголовки, нужные клиентам; без support-url, subscription-userinfo, announce и т.п.
    profile-title в формате base64:… как у апстрима.
    """
    title = _DEACTIVATED_TITLE if deactivated else _ACTIVE_TITLE
    title_b64 = base64.b64encode(title.encode("utf-8")).decode("ascii")
    fname = _DEACTIVATED_FILENAME if deactivated else _ACTIVE_FILENAME
    return {
        "Cache-Control": "no-store",
        "profile-title": f"base64:{title_b64}",
        "profile-update-interval": "1",
        "Content-Disposition": _content_disposition_filename(fname),
        "X-Content-Type-Options": "nosniff",
    }
