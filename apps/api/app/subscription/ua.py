from __future__ import annotations

import re

# Выходные форматы подписки (план §4).
FORMAT_HAPP = "happ"
FORMAT_FLCLASH = "flclash"
FORMAT_THRONE = "throne"

OUTPUT_FORMAT_AUTO = "auto"
OUTPUT_FORMAT_FORCE_HAPP = "force_happ"
OUTPUT_FORMAT_FORCE_FLCLASH = "force_flclash"
OUTPUT_FORMAT_FORCE_THRONE = "force_throne"
VALID_OUTPUT_FORMAT_MODES = frozenset(
    {
        OUTPUT_FORMAT_AUTO,
        OUTPUT_FORMAT_FORCE_HAPP,
        OUTPUT_FORMAT_FORCE_FLCLASH,
        OUTPUT_FORMAT_FORCE_THRONE,
    }
)


def resolve_output_format(user_agent: str | None, mode: str = OUTPUT_FORMAT_AUTO) -> str:
    if mode == OUTPUT_FORMAT_FORCE_HAPP:
        return FORMAT_HAPP
    if mode == OUTPUT_FORMAT_FORCE_FLCLASH:
        return FORMAT_FLCLASH
    if mode == OUTPUT_FORMAT_FORCE_THRONE:
        return FORMAT_THRONE
    return detect_subscription_format(user_agent)


def detect_subscription_format(user_agent: str | None) -> str:
    ua = (user_agent or "").strip()
    if re.search(r"(?i)happ", ua):
        return FORMAT_HAPP
    if re.search(r"(?i)throne", ua):
        return FORMAT_THRONE
    if re.search(r"(?i)flclash|clash[- ]?meta|mihomo|stash", ua):
        return FORMAT_FLCLASH
    return FORMAT_FLCLASH
