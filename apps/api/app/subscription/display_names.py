from __future__ import annotations

import re
from collections import defaultdict

from app.subscription.nodes import ProxyNode
from app.subscription.server_slots import (
    ServerSlotState,
    assign_group_slots,
    next_free_slot,
    node_identity,
    prune_slot_state,
    unique_identities_for_indices,
)
from app.subscription.server_slots import _FREED_SLOTS_KEY

NAME_MODE_BLANC = "blanc"
NAME_MODE_LIBERTY = "liberty"
NAME_MODE_SLOVO = "slovo"
NAME_MODE_CUSTOM = "custom"
NAME_MODE_NONE = "none"
VALID_NAME_MODES = frozenset({
    NAME_MODE_BLANC,
    NAME_MODE_LIBERTY,
    NAME_MODE_SLOVO,
    NAME_MODE_CUSTOM,
    NAME_MODE_NONE,
})

_FLAG_START = re.compile(r"^([\U0001F1E6-\U0001F1FF]{2})\s*")
_PARENS = re.compile(r"\([^)]*\)")
_WHITELIST_HASH = re.compile(r"Whitelist#\d+", re.IGNORECASE)
_SERVICE_NAME = re.compile(r"→\s*Blanc\s*VPN\s*$", re.IGNORECASE)
_SLOVO_ROMAN = re.compile(r"\s+(I|II|III|IV|V)\b(?=\s*[·]|$)")
_SLOVO_ROMAN_END = re.compile(r"\s+(I|II|III|IV|V)$")
_SLOVO_WHITELIST_ROMAN = re.compile(r"\b(III|II|IV|V|I)\b", re.IGNORECASE)


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


def _strip_liberty_marks(raw: str) -> tuple[str, str]:
    m = _FLAG_START.match(raw.strip())
    flag = m.group(1) if m else ""
    body = raw[m.end() :] if m else raw
    body = re.sub(r"\([^)]*\)", " ", body)
    body = re.sub(r"\b(bypass|gaming)\b", " ", body, flags=re.IGNORECASE)
    # Убираем декоративные эмодзи/иконки провайдера, оставляя буквы, цифры и дефисы.
    body = re.sub(r"^[^\wА-Яа-яЁё]+", " ", body)
    body = re.sub(r"[^\wА-Яа-яЁё\s-]+", " ", body)
    body = re.sub(r"[-–]\s*\d+\s*$", "", body)
    body = re.sub(r"\s+", " ", body).strip(" ,-")
    return flag, body


def _canonical_liberty_name_for_proxy(name: str) -> str:
    raw = name.strip()
    if not raw:
        return ""
    lower = raw.lower()
    flag, country = _strip_liberty_marks(raw)
    if not country:
        return raw
    if "бс" in lower:
        return f"{flag} 🏳️ Whitelist, {country}".strip()
    if "bypass" in lower:
        return f"{flag} {country} Bypass".strip()
    if "gaming" in lower:
        return f"{flag} {country} Gaming".strip()
    if "💳" in raw or "payment" in lower or "pay" in lower:
        return f"{flag} {country} Payment".strip()
    return f"{flag} {country}".strip()


def _slovo_roman_to_int(roman: str) -> int | None:
    mapping = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
    return mapping.get(roman.upper())


def _slovo_strip_roman(country_part: str) -> tuple[str, int | None]:
    for pattern in (_SLOVO_ROMAN, _SLOVO_ROMAN_END):
        match = pattern.search(country_part)
        if not match:
            continue
        number = _slovo_roman_to_int(match.group(1))
        stripped = pattern.sub("", country_part).strip()
        return stripped, number
    return country_part, None


def _slovo_whitelist_number(raw: str) -> int:
    for roman, value in (("III", 3), ("II", 2), ("IV", 4), ("V", 5), ("I", 1)):
        if re.search(rf"\b{roman}\b", raw, re.IGNORECASE):
            return value
    return 1


def _slovo_suffix_label(suffix: str) -> str:
    lower = suffix.lower()
    if "ru сайты" in lower or "ru direct" in lower:
        return "RU Direct"
    if "ru bypass" in lower:
        return "RU Bypass"
    if "все через vpn" in lower or "all proxy" in lower:
        return "ALL Proxy"
    return suffix.strip()


def _canonical_slovo_name_for_proxy(name: str) -> str:
    raw = name.strip()
    if not raw:
        return ""
    lower = raw.lower()
    flag_m = _FLAG_START.match(raw)
    flag = flag_m.group(1) if flag_m else ""
    body = raw[flag_m.end() :].strip() if flag_m else raw

    if "бел" in lower and ("обход бел" in lower or _SLOVO_WHITELIST_ROMAN.search(body)):
        return f"{flag or '🇷🇺'} 🏳️ Whitelist #{_slovo_whitelist_number(raw)}"

    parts = [p.strip() for p in body.split("·", 1)]
    country_part = parts[0].strip()
    suffix_raw = parts[1].strip() if len(parts) > 1 else ""

    country_name, number = _slovo_strip_roman(country_part)
    label = f"{country_name} #{number}" if number is not None else country_name
    suffix = _slovo_suffix_label(suffix_raw)
    if suffix:
        return f"{flag} {label} [{suffix}]".strip()
    return f"{flag} {label}".strip()


_SLOVO_ROUTE_SUFFIX = re.compile(r"\s+\[(RU Direct|RU Bypass|ALL Proxy)\]\s*$", re.IGNORECASE)


def strip_slovo_route_suffix(name: str) -> str:
    """Убирает [RU Direct]/[ALL Proxy] — для Throne/FlClash со своими routes."""
    return _SLOVO_ROUTE_SUFFIX.sub("", name.strip())


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
    slot_state: ServerSlotState | None = None,
) -> ServerSlotState:
    """Нормализация отображаемых имён; правит node.name на месте. Возвращает обновлённую карту слотов."""
    state: ServerSlotState = dict(slot_state or {})
    mode = mode if mode in VALID_NAME_MODES else NAME_MODE_BLANC
    if mode == NAME_MODE_NONE:
        return state

    parsed_rules = _parse_custom_rules(custom_rules) if mode == NAME_MODE_CUSTOM else []

    if mode == NAME_MODE_SLOVO:
        for n in nodes:
            c = _canonical_slovo_name_for_proxy(n.name)
            if c:
                n.name = c
        return state

    keys: list[str | None] = []
    for n in nodes:
        if mode == NAME_MODE_CUSTOM:
            c = _custom_name_for_proxy(n.name, parsed_rules)
        elif mode == NAME_MODE_LIBERTY:
            c = _canonical_liberty_name_for_proxy(n.name)
        else:
            c = _canonical_name_for_proxy(n.name)
        keys.append(c if c else None)

    groups: dict[str, list[int]] = defaultdict(list)
    for i, k in enumerate(keys):
        if k:
            groups[k].append(i)

    for k, idxs in groups.items():
        idxs_sorted = sorted(idxs)
        identities = unique_identities_for_indices(nodes, idxs_sorted)
        if len(idxs_sorted) == 1:
            ident = identities[0]
            prev_map = state.get(k, {})
            prev_slots = {key: val for key, val in prev_map.items() if key != _FREED_SLOTS_KEY}
            group_slots = assign_group_slots(prev_map, identities)
            state[k] = group_slots
            slot = group_slots[ident]
            # Один сервер: без # только если это единственный слот #1 с нуля; иначе сохраняем #N.
            nodes[idxs_sorted[0]].name = (
                k if slot == 1 and ident not in prev_slots else f"{k} #{slot}"
            )
            continue

        group_slots = assign_group_slots(state.get(k, {}), identities)
        state[k] = group_slots
        used_slots: set[int] = set()
        for idx, ident in zip(idxs_sorted, identities):
            slot = next_free_slot(group_slots[ident], used_slots)
            nodes[idx].name = f"{k} #{slot}"

    return prune_slot_state(state, set(groups.keys()))
