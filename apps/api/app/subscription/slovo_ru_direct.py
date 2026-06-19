from __future__ import annotations

import json
import logging
from typing import Any

from app.subscription.parser import filter_slovo_configs

logger = logging.getLogger(__name__)

SLOVO_RU_DIRECT_ROUTE_PREFIXES = (
    "domain:",
    "full:",
    "geosite:",
    "regexp:",
    "keyword:",
    "suffix:",
)

SLOVO_RU_DIRECT_ROUTE_HINT = (
    "По одному правилу на строку. Поддерживаются префиксы: "
    + ", ".join(SLOVO_RU_DIRECT_ROUTE_PREFIXES)
    + ". Пустые строки и строки с # игнорируются."
)


def parse_slovo_ru_direct_routes(text: str) -> list[str]:
    routes: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        routes.append(line)
    return routes


def validate_slovo_ru_direct_routes(text: str) -> list[str]:
    routes = parse_slovo_ru_direct_routes(text)
    for line in routes:
        if not any(line.startswith(prefix) for prefix in SLOVO_RU_DIRECT_ROUTE_PREFIXES):
            raise ValueError(
                f"Некорректное правило direct-маршрута: {line!r}. "
                f"Допустимые префиксы: {', '.join(SLOVO_RU_DIRECT_ROUTE_PREFIXES)}"
            )
    return routes


def extract_provider_slovo_ru_direct_domains(body: str) -> list[str]:
    text = body.strip()
    if not (text.startswith("[") or text.startswith("{")):
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    for config in filter_slovo_configs(data):
        remarks = str(config.get("remarks") or "").lower()
        if "ru сайты работают" not in remarks:
            continue
        rules = (config.get("routing") or {}).get("rules") or []
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("outboundTag") != "direct":
                continue
            domains = rule.get("domain")
            if isinstance(domains, list):
                return [str(part) for part in domains if part]
    return []


def apply_slovo_ru_direct_routes_to_config(config: dict[str, Any], routes: list[str]) -> None:
    """Заменяет direct domain whitelist в [RU Direct] на routes (полностью)."""
    if "[RU Direct]" not in str(config.get("remarks") or ""):
        return
    routing = config.get("routing")
    if not isinstance(routing, dict):
        routing = {"domainStrategy": "IPIfNonMatch", "rules": []}
        config["routing"] = routing
    rules = routing.get("rules")
    if not isinstance(rules, list):
        rules = []
        routing["rules"] = rules

    for i, rule in enumerate(rules):
        if not isinstance(rule, dict) or rule.get("outboundTag") != "direct":
            continue
        if "domain" in rule:
            rules[i] = {**rule, "domain": list(routes)}
            return
    rules.append({"type": "field", "outboundTag": "direct", "domain": list(routes)})


def format_routes_for_textarea(routes: list[str]) -> str:
    return "\n".join(routes)
