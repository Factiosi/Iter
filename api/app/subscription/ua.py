from __future__ import annotations

import re

# Выходные форматы подписки (план §4).
FORMAT_HAPP = "happ"
FORMAT_FLCLASH = "flclash"
FORMAT_THRONE = "throne"


def detect_subscription_format(user_agent: str | None) -> str:
    ua = (user_agent or "").strip()
    if re.search(r"(?i)happ", ua):
        return FORMAT_HAPP
    if re.search(r"(?i)throne", ua):
        return FORMAT_THRONE
    if re.search(r"(?i)flclash|clash[- ]?meta|mihomo|stash", ua):
        return FORMAT_FLCLASH
    return FORMAT_FLCLASH
