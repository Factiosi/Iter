# CORP VPN proxy

Отдельный sidecar для выдачи подписок CORP VPN. **Не входит** в `docker-compose.yml` Iter Portal — запускается вручную или через systemd.

Переиспользует subscription pipeline из `apps/api` (`build_subscription_response`) — те же форматы, что у Iter Portal.

## Запуск

```bash
export CORP_MASTER_SUBSCRIPTION_URL=https://…   # или CORP_MASTER_URL_1 … _4
export CORP_NAME_MODE=slovo                     # см. Slovo VPN ниже
python3 ops/corpvpn/corpvpn_proxy.py
```

По умолчанию: `127.0.0.1:8080`, healthcheck `GET /healthz`.

Пути подписки: `/CorpVpnSubscription1_` … `/CorpVpnSubscription4_`.

## Slovo VPN (текущий провайдер)

Пример env: [`env.slovo.example`](env.slovo.example).

| Переменная | Значение |
|------------|----------|
| `CORP_NAME_MODE` | `slovo` |
| `CORP_MASTER_SUBSCRIPTION_URL` | `https://sub.slovovpn.com/sub/…` |
| `CORP_OUTPUT_FORMAT_MODE` | `auto` (рекомендуется) |

**Форматы по клиенту** (как в Iter):

| Клиент | Формат |
|--------|--------|
| Happ | Xray JSON **без** `routing` в узлах + заголовок `routing` (`CORP Route` deeplink) |
| Throne | base64 `vless://` share links (mlkem + xhttp) |
| FlClash | Clash YAML |

**Имена серверов** (preset `slovo`):

- `🇪🇪 Эстония #1 [RU Direct]`
- `🇸🇪 Швеция #2 [ALL Proxy]`
- `🇷🇺 🏳️ Whitelist #2`

Слоты имён (`corpvpn-slot-state.json`) для `slovo` **не используются** — можно не удалять файл, но он не влияет на имена.

**Happ (Slovo):** по умолчанию `CORP_HAPP_ROUTING_DEEPLINK=1` — глобальный маршрут через заголовок `routing` (как у LIBERTY), `routing` в JSON каждого сервера удаляется. Так Happ стабильно обновляет подписку и профиль маршрутизации. Отключить: `CORP_HAPP_ROUTING_DEEPLINK=0` (встроенный routing провайдера в узлах, как Iter Portal).

**После перехода с LIBERTY/Blanc:**

1. Выставить `CORP_NAME_MODE=slovo` и новый master URL.
2. Перезапустить `corpvpn_proxy.py` (или systemd).
3. В Happ один раз удалить старый «Iter Route» / «CORP Route», если был сохранён ранее — затем обновить подписку.
4. Обновить подписку во всех клиентах.

`CORP_ROUTE_NAME` / `CORP_BYPASS_RENDER_MODE` актуальны только для режима `liberty`.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `CORP_APP_PATH` | `apps/api` в корне репо | Импорт модулей `app.subscription.*` |
| `CORP_BIND_HOST` / `CORP_PORT` | `127.0.0.1` / `8080` | Bind |
| `CORP_MASTER_SUBSCRIPTION_URL` | — | Общий master URL |
| `CORP_MASTER_URL_1` … `_4` | — | Master URL на слот |
| `CORP_NAME_MODE` | `blanc` | `blanc` / `liberty` / `slovo` / `custom` / `none` |
| `CORP_NAME_RULES` | — | Regex-правила при `custom` |
| `CORP_OUTPUT_FORMAT_MODE` | `auto` | `auto` / `force_happ` / `force_flclash` / `force_throne` |
| `CORP_BYPASS_RENDER_MODE` | `socks` | `socks` / `chain` / `both` (LIBERTY) |
| `CORP_CACHE_TTL` | `300` | Кэш ответа, сек |
| `CORP_SLOT_STATE_FILE` | см. скрипт | JSON слотов имён (blanc/liberty) |
| `CORP_DEACTIVATED` / `CORP_DEACTIVATED_N` | — | Poisoning слота |
| `CORP_PROFILE_PREFIX` | `CORP VPN` | `profile-title` |
| `CORP_ROUTE_NAME` | `CORP Route` | Имя Happ routing-профиля (deeplink) |
| `CORP_HAPP_ROUTING_DEEPLINK` | `1` для `slovo`, иначе `0` | Slovo+Happ: глобальный маршрут в заголовке, без routing в JSON узлов |
| `CORP_ROUTE_DIRECT_SITES` | — | Свой список `directsites` для deeplink (по строке, префиксы как у Slovo) |
| `CORP_SLOVO_RU_DIRECT_ROUTES` | — | То же для RU Direct whitelist; при deeplink попадает в `directsites` |
| `CORP_CLASH_GROUP_NAME` | `CORP VPN` | Clash group |

Состояние слотов по умолчанию: `corpvpn-slot-state.json` рядом со скриптом (Windows) или `/var/lib/corpvpn/slot-state.json` (Linux).

## Деплой на сервер

1. Обновить код репозитория (минимум `apps/api/app/subscription/` и `ops/corpvpn/`).
2. Убедиться, что `CORP_APP_PATH` указывает на актуальный `apps/api`.
3. Применить env (см. `env.slovo.example`), перезапустить сервис.
4. Проверить слот: `curl -fsS -H "User-Agent: Throne/1.0" http://127.0.0.1:8080/CorpVpnSubscription1_ | head -c 80`
