from __future__ import annotations

import re
from collections import defaultdict

from app.subscription.nodes import ProxyNode

NAME_MODE_BLANC = "blanc"
NAME_MODE_CUSTOM = "custom"
NAME_MODE_NONE = "none"
VALID_NAME_MODES = frozenset({NAME_MODE_BLANC, NAME_MODE_CUSTOM, NAME_MODE_NONE})

_FLAG_START = re.compile(r"^([\U0001F1E6-\U0001F1FF]{2})\s*")
_PARENS = re.compile(r"\([^)]*\)")
_WHITELIST_HASH = re.compile(r"Whitelist#\d+", re.IGNORECASE)
_SERVICE_NAME = re.compile(r"→\s*Blanc\s*VPN\s*$", re.IGNORECASE)


def _strip_extra_word_and_parens(s: str) -> str:
    s = _PARENS.sub("", s)
    s = re.sub(r",\s*Extra\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*Extra\s*$", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip(" ,")


def _canonical_whitelist_line(raw: str) -> str:
    s = raw
    s = _WHITELIST_HASH.sub("Whitelist", s)
    s = _PARENS.sub("", s)
    s = re.sub(r"\bExtra\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" ,")

    m = _FLAG_START.match(s)
    rest = s[m.end() :] if m else s
    rest = rest.strip()
    if "," in rest:
        country = rest.split(",", 1)[0].strip()
    else:
        country = rest
    country = re.sub(r"^Whitelist\s*,?\s*", "", country, flags=re.IGNORECASE).strip()
    if m:
        return f"{m.group(1)} 🏳️ Whitelist, {country}"
    return f"🏳️ Whitelist, {country}"


def _canonical_extra_line(raw: str) -> str:
    m = _FLAG_START.match(raw)
    flag = m.group(1) if m else ""
    body = raw[m.end() :] if m else raw
    body = _strip_extra_word_and_parens(body)

    parts = [p.strip() for p in body.split(",") if p.strip()]
    while parts and parts[-1].lower() == "extra":
        parts.pop()

    if not parts:
        return f"{flag}".strip() if flag else body.strip()

    country = parts[-1]
    if len(parts) >= 2 and parts[-1] == parts[-2]:
        country = parts[-1]

    return f"{flag} {country}".strip()


def _canonical_name_for_proxy(name: str) -> str:
    raw = name.strip()
    if not raw or _SERVICE_NAME.search(raw):
        return ""
    if "Whitelist" in raw:
        return _canonical_whitelist_line(raw)
    return _canonical_extra_line(raw)


def _parse_custom_rules(rules_text: str) -> list[tuple[re.Pattern[str], str]]:
    rules: list[tuple[re.Pattern[str], str]] = []
    for raw_line in rules_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=>" not in line:
            raise ValueError(f"Некорректное правило имени сервера: {line}")
        pattern, replacement = [p.strip() for p in line.split("=>", 1)]
        if not pattern:
            raise ValueError(f"Пустой regex в правиле имени сервера: {line}")
        replacement = re.sub(r"\$(\d+)", r"\\\1", replacement)
        rules.append((re.compile(pattern), replacement))
    return rules


def _custom_name_for_proxy(name: str, rules: list[tuple[re.Pattern[str], str]]) -> str:
    raw = name.strip()
    for pattern, replacement in rules:
        if pattern.search(raw):
            return pattern.sub(replacement, raw).strip()
    return raw


def normalize_server_names(
    nodes: list[ProxyNode],
    *,
    mode: str = NAME_MODE_BLANC,
    custom_rules: str = "",
) -> None:
    """Нормализация отображаемых имён; правит node.name на месте."""
    mode = mode if mode in VALID_NAME_MODES else NAME_MODE_BLANC
    if mode == NAME_MODE_NONE:
        return

    parsed_rules = _parse_custom_rules(custom_rules) if mode == NAME_MODE_CUSTOM else []
    keys: list[str | None] = []
    for n in nodes:
        c = _custom_name_for_proxy(n.name, parsed_rules) if mode == NAME_MODE_CUSTOM else _canonical_name_for_proxy(n.name)
        keys.append(c if c else None)

    groups: dict[str, list[int]] = defaultdict(list)
    for i, k in enumerate(keys):
        if k:
            groups[k].append(i)

    for k, idxs in groups.items():
        idxs_sorted = sorted(idxs)
        if len(idxs_sorted) == 1:
            nodes[idxs_sorted[0]].name = k
        else:
            for num, idx in enumerate(idxs_sorted, start=1):
                nodes[idx].name = f"{k} #{num}"
