# CORP VPN proxy

Отдельный sidecar для выдачи подписок CORP VPN. **Не входит** в `docker-compose.yml` Iter Portal — запускается вручную или через systemd.

Переиспользует subscription pipeline из `apps/api` (`build_subscription_response`).

## Запуск

```bash
export CORP_MASTER_SUBSCRIPTION_URL=https://…   # или CORP_MASTER_URL_1 … _4
python3 ops/corpvpn/corpvpn_proxy.py
```

По умолчанию: `127.0.0.1:8080`, healthcheck `GET /healthz`.

Пути подписки: `/CorpVpnSubscription1_` … `/CorpVpnSubscription4_`.

## Переменные

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `CORP_APP_PATH` | `apps/api` в корне репо | Импорт модулей `app.subscription.*` |
| `CORP_BIND_HOST` / `CORP_PORT` | `127.0.0.1` / `8080` | Bind |
| `CORP_MASTER_SUBSCRIPTION_URL` | — | Общий master URL |
| `CORP_MASTER_URL_1` … `_4` | — | Master URL на слот |
| `CORP_NAME_MODE` | `blanc` | `server_name_mode` |
| `CORP_OUTPUT_FORMAT_MODE` | `auto` | Как в портале |
| `CORP_BYPASS_RENDER_MODE` | `socks` | `socks` / `chain` / `both` |
| `CORP_CACHE_TTL` | `300` | Кэш ответа, сек |
| `CORP_SLOT_STATE_FILE` | см. скрипт | JSON слотов имён |
| `CORP_DEACTIVATED` / `CORP_DEACTIVATED_N` | — | Poisoning слота |
| `CORP_PROFILE_PREFIX` | `CORP VPN` | `profile-title` |
| `CORP_ROUTE_NAME` | `CORP Route` | Happ routing |
| `CORP_CLASH_GROUP_NAME` | `CORP VPN` | Clash group |

Состояние слотов по умолчанию: `corpvpn-slot-state.json` рядом со скриптом (Windows) или `/var/lib/corpvpn/slot-state.json` (Linux).
