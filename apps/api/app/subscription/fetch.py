from __future__ import annotations

import httpx

MAX_BODY_BYTES = 8 * 1024 * 1024

# Запрос к мастеру всегда с одним UA (Happ Android), иначе часть провайдеров не отдаёт тело.
MASTER_SUBSCRIPTION_FETCH_USER_AGENT = "Happ/3.15.2/Android/1733565"


def fetch_master_subscription_sync(url: str) -> tuple[str, str]:
    headers = {"User-Agent": MASTER_SUBSCRIPTION_FETCH_USER_AGENT}
    with httpx.Client(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(max_connections=5),
    ) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        ct = r.headers.get("content-type", "") or ""
        raw = r.content
        if len(raw) > MAX_BODY_BYTES:
            raise ValueError("Подписка слишком большая")
        text = raw.decode("utf-8", errors="replace")
        return ct, text
