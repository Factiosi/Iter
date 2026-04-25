from __future__ import annotations

import copy

from app.subscription.nodes import ProxyNode

# Невалидные для реального подключения, но синтаксически похожие на UUID/порт.
_POISON_UUID = "66666666-6666-6666-6666-666666666666"
_POISON_PORT = 666


def apply_poisoning(nodes: list[ProxyNode]) -> list[ProxyNode]:
    """
    Режим отозванной подписки: имена без флагов, одинаковый сломанный uuid и порт 666.
    Имена уникальны для Clash (суффикс #N).
    """
    out: list[ProxyNode] = []
    for i, n in enumerate(nodes, start=1):
        c = copy.deepcopy(n)
        c.uuid = _POISON_UUID
        c.port = _POISON_PORT
        c.name = f"Не доступен #{i}" if len(nodes) > 1 else "Не доступен"
        out.append(c)
    return out
