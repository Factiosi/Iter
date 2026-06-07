from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProxyNode:
    """Узел прокси для внутреннего представления (Clash YAML и/или URI)."""

    name: str
    uuid: str
    server: str
    port: int
    protocol: str = "vless"
    network: str = "tcp"
    tls: bool = False
    sni: str | None = None
    host: str | None = None
    path: str | None = None
    client_fingerprint: str | None = None
    # REALITY
    pbk: str | None = None
    sid: str | None = None
    fp: str | None = None
    flow: str | None = None
    password: str | None = None
    alpn: list[str] | None = None
    skip_cert_verify: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
