from __future__ import annotations

import json
import re
from typing import Any

from app.subscription.nodes import ProxyNode

_WHITELIST_NUM = re.compile(r"Whitelist#(\d+)", re.IGNORECASE)
_PARENS_SEG = re.compile(r"\([^)]*\)")

ServerSlotState = dict[str, dict[str, int]]

# Внутри карты группы: список освободившихся номеров после ухода host:port.
_FREED_SLOTS_KEY = "__freed__"


def _parens_tag(raw: str) -> str:
    """Оператор в скобках (Yota, Beeline) — стабилен, в отличие от ws-path."""
    tags = [t.strip().lower() for t in _PARENS_SEG.findall(raw) if t.strip()]
    return "|".join(tags)


def node_identity(node: ProxyNode) -> str:
    """
    Стабильный ключ узла внутри группы.
    Нельзя использовать только host:port — у Whitelist десятки узлов на одном IP.
    path не используем — у Blanc он ротируется.
    """
    raw = node.name
    tag = _parens_tag(raw)
    wl = _WHITELIST_NUM.search(raw)
    if wl:
        base = f"wl:{wl.group(1)}:{node.server}:{node.port}"
        return f"{base}|{tag}" if tag else base

    label = _PARENS_SEG.sub("", raw)
    label = re.sub(r",?\s*Extra\s*", " ", label, flags=re.IGNORECASE)
    label = re.sub(r"\s+", " ", label).strip().lower()[:160]
    parts = [node.server, str(node.port), label or raw.strip().lower()[:80]]
    if tag:
        parts.append(f"p={tag}")
    if node.sni:
        parts.append(f"sni={node.sni}")
    if node.host:
        parts.append(f"host={node.host}")
    return "|".join(parts)


def unique_identities_for_indices(nodes: list[ProxyNode], indices: list[int]) -> list[str]:
    """Один identity на строку подписки; при коллизии — суффикс ~1, ~2."""
    out: list[str] = []
    seen: dict[str, int] = {}
    for idx in indices:
        base = node_identity(nodes[idx])
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.append(base if n == 0 else f"{base}~{n}")
    return out


def next_free_slot(slot: int, used: set[int]) -> int:
    while slot in used:
        slot += 1
    used.add(slot)
    return slot


def _identity_sort_key(ident: str) -> tuple:
    def host_key(host: str) -> str:
        try:
            return ".".join(f"{int(part):03d}" for part in host.split("."))
        except ValueError:
            return host

    if ident.startswith("wl:"):
        try:
            _tag, num, host, port_s = ident.split(":", 3)
            return (0, f"{int(num):08d}", host_key(host), f"{int(port_s):05d}", ident)
        except (ValueError, IndexError):
            return (0, ident)
    if "|" in ident:
        host, port_s, *_rest = ident.split("|", 2)
        try:
            return (1, host_key(host), f"{int(port_s):05d}", ident)
        except ValueError:
            return (1, ident)
    host, _, port_s = ident.partition(":")
    try:
        return (2, host_key(host), f"{int(port_s or '443'):05d}", ident)
    except ValueError:
        return (2, host, port_s)


def _dedupe_slot_numbers(mapping: dict[str, int]) -> None:
    """Два разных identity не должны делить один #N (чинит устаревшее состояние в БД)."""
    occupied: dict[int, str] = {}
    for ident, slot in list(mapping.items()):
        if ident == _FREED_SLOTS_KEY:
            continue
        if slot not in occupied:
            occupied[slot] = ident
            continue
        next_slot = 1
        all_slots = set(occupied) | set(mapping.values())
        while next_slot in all_slots:
            next_slot += 1
        mapping[ident] = next_slot
        occupied[next_slot] = ident


def assign_group_slots(prev: dict[str, int], identities: list[str]) -> dict[str, int]:
    """
    Сохраняет номера для известных host:port, освобождённые слоты отдаёт новым узлам.
    Возвращает карту текущих identities + __freed__ с незанятыми номерами.
    """
    identity_set = set(identities)
    prev_slots = {k: v for k, v in prev.items() if k != _FREED_SLOTS_KEY}
    pooled_freed = list(prev.get(_FREED_SLOTS_KEY, []))

    result: dict[str, int] = {}
    used: set[int] = set()

    for ident in identities:
        if ident in prev_slots:
            slot = prev_slots[ident]
            result[ident] = slot
            used.add(slot)

    departed_freed = sorted(
        slot for ident, slot in prev_slots.items() if ident not in identity_set
    )
    freed_queue = sorted(set(pooled_freed + departed_freed))
    new_idents = sorted(
        (ident for ident in identities if ident not in prev_slots),
        key=_identity_sort_key,
    )

    freed_iter = iter(freed_queue)
    next_slot = (max(used) + 1) if used else 1

    for ident in new_idents:
        try:
            slot = next(freed_iter)
        except StopIteration:
            while next_slot in used:
                next_slot += 1
            slot = next_slot
            next_slot += 1
        result[ident] = slot
        used.add(slot)

    leftover_freed = sorted(s for s in freed_queue if s not in used)
    if leftover_freed:
        result[_FREED_SLOTS_KEY] = leftover_freed
    _dedupe_slot_numbers(result)
    return result


def parse_slot_state(raw: str | None) -> ServerSlotState:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out: ServerSlotState = {}
    for group_key, mapping in data.items():
        if not isinstance(group_key, str) or not isinstance(mapping, dict):
            continue
        slots: dict[str, int] = {}
        for ident, num in mapping.items():
            if ident == _FREED_SLOTS_KEY:
                if isinstance(num, list):
                    cleaned = sorted({int(x) for x in num if isinstance(x, int) and x >= 1})
                    if cleaned:
                        slots[_FREED_SLOTS_KEY] = cleaned  # type: ignore[assignment]
                continue
            if isinstance(ident, str) and isinstance(num, int) and num >= 1:
                slots[ident] = num
        if slots:
            out[group_key] = slots
    return out


def dump_slot_state(state: ServerSlotState) -> str:
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"))


def prune_slot_state(state: ServerSlotState, active_groups: set[str]) -> ServerSlotState:
    return {k: v for k, v in state.items() if k in active_groups}
