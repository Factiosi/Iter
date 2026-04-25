# Iter Portal

Внутренний приватный проект портала `iter.factiosi.com`: авторизация по email-коду, whitelist пользователей, генерация VPN-ссылок, публичная выдача подписки под разные клиенты и Docker-деплой за хостовым nginx.

README написан для себя, не для публичного GitHub. Тут важно не продать проект, а через несколько лет быстро понять, где что лежит, почему так сделано и как это чинить.

## Что делает проект

Портал хранит whitelist email-адресов и для каждого пользователя может создать основную VPN-ссылку. Пользователь видит deeplink для Happ и FlClash, а также прямую ссылку конфигурации. Публичная ссылка вида `/config/{slug}` не требует JWT: по ней VPN-клиенты забирают подписку.

Мастер-подписка берётся из админки. Сейчас исторически использовалась Blanc VPN master link, которая нормально отдаёт тело только под Happ, поэтому сервер сам ходит к мастер-ссылке фиксированным Android Happ User-Agent, парсит VLESS-ноды и затем рендерит ответ под клиентский User-Agent:

- Happ: base64 bundle из VLESS URI.
- Throne: base64 bundle из VLESS URI, с явным `type=tcp` для TCP.
- FlClash: Clash YAML с группой `Iter VPN` и правилом `MATCH,Iter VPN`.

Из апстрим-заголовков намеренно не прокидываются `support-url`, `subscription-userinfo`, `announce` и похожая лишняя информация. Портал сам выставляет `profile-title`, `Content-Disposition`, `Cache-Control` и базовые безопасные заголовки.

## Текущая структура

```text
.
├── apps/
│   ├── api/                 # FastAPI backend
│   │   ├── app/
│   │   │   ├── routers/     # HTTP endpoints
│   │   │   ├── services/    # бизнес-логика
│   │   │   └── subscription/# fetch/parse/render/poison pipeline подписки
│   │   ├── scripts/         # небольшие ручные проверки API/SMTP/SQLite
│   │   └── tests/           # pytest
│   └── web/                 # React/Vite frontend
│       ├── deploy/          # nginx config внутри web container
│       ├── public/          # favicon/app icons
│       └── src/
├── assets/
│   └── brand/               # исходники бренда и логотипов
├── ops/
│   └── deploy/              # deploy docs, env template, host nginx example
├── scripts/                 # repo-level helper scripts
├── docker-compose.yml       # production stack: api + web
└── .env.example             # root env template for Docker Compose
```

Почему так:

- `apps/api` и `apps/web` отделяют два приложения от инфраструктуры.
- `assets/brand` хранит исходные изображения не внутри фронта, потому что они используются и для сайта, и для писем/иконок.
- `ops/deploy` хранит только эксплуатационные вещи. Старые systemd/uvicorn-only файлы удалены после перехода на Docker.
- Runtime-данные (`apps/api/data/iter.db`, `.env`) не коммитятся.

## Backend

Основные файлы:

- `apps/api/app/main.py` - создание FastAPI app, CORS, роутеры, миграция SQLite на старте, фоновая очистка poisoned-ссылок каждые 12 часов.
- `apps/api/app/config.py` - env-настройки через Pydantic Settings.
- `apps/api/app/database.py` - SQLAlchemy engine/session, простая SQLite migration/backfill логика.
- `apps/api/app/models.py` - таблицы.
- `apps/api/app/routers/auth_routes.py` - вход пользователя по email-коду.
- `apps/api/app/routers/admin_routes.py` - whitelist, роли, master subscription settings.
- `apps/api/app/routers/vpn_routes.py` - генерация основной и гостевых VPN-ссылок.
- `apps/api/app/routers/portal_public_routes.py` - публичные `/config/{slug}` и `/{localpart}/deeplink`.

### БД

Прод использует SQLite:

```text
apps/api/data/iter.db
```

В Docker она примонтирована в контейнер как:

```text
/app/data/iter.db
```

Важные таблицы:

- `allowed_emails` - whitelist и роль (`user`, `moderator`).
- `portal_settings` - master URL и настройки трансформации подписки.
- `user_main_vpn_links` - основная ссылка пользователя.
- `guest_vpn_links` - гостевые ссылки.
- `otp_challenges` - одноразовые email-коды.

`migrate_sqlite_schema()` добавляет новые колонки через `ALTER TABLE`, потому что SQLite `create_all` не обновляет существующие таблицы. Это не полноценный Alembic, но для маленького приватного проекта достаточно. Перед рискованными изменениями на сервере лучше вручную копировать `iter.db` в `~/iter-backups`.

### VPN link lifecycle

Пользователь в whitelist может создать основную ссылку. Если пользователь удаляется из whitelist, строка VPN-ссылки не удаляется сразу. Она переводится в `poisoning`:

- `vpn_link_status = poisoning`
- `poisoning_started_at = now`
- `purge_deadline_at = now + 31 days`
- `config_fetched_after_poison_at = NULL`

При обращении к `/config/{slug}` в poisoned-состоянии сервер отдаёт поломанную подписку:

- UUID всех нод: `66666666-6666-6666-6666-666666666666`
- порт: `666`
- имя: `Не доступен #N`
- `profile-title`: `Подписка деактивирована`

Если email снова добавлен в whitelist, `restore_access()` возвращает ссылки в `active`. Если прошло 31 день, фоновая очистка удалит poisoned-ссылки.

### Счётчик обновлений

В админке колонка `Кол-во обновлений` берётся из `user_main_vpn_links.config_fetch_count`.

Логика:

- основной ссылки нет: `Не активен`
- ссылка создана, но обращений не было: `0`
- каждое успешное получение `/config/{slug}` или `/{localpart}/deeplink`: `+1`

Счётчик увеличивается только после успешного fetch/parse/render pipeline, то есть 502/ошибки мастер-ссылки не считаются.

## Subscription pipeline

Код живёт в `apps/api/app/subscription/`.

Порядок:

1. `fetch.py` скачивает master subscription фиксированным UA:

   ```text
   Happ/3.15.2/Android/1733565
   ```

2. `parser.py` парсит base64/plain/YAML и приводит всё к `ProxyNode`.
3. `pipeline.py` выбирает трансформацию:
   - active: правила имён серверов;
   - poisoning: `apply_poisoning()`.
4. `ua.py` выбирает выходной формат.
5. `render.py` рендерит Happ/Throne/FlClash.
6. `out_headers.py` собирает чистые headers.

### Настройки подписки в админке

В блоке мастер-ссылки есть настройки, которые сохраняются в `portal_settings`.

`server_name_mode`:

- `blanc` - текущий встроенный preset под Blanc VPN. Убирает `Extra`, схлопывает дубли стран, отдельно обрабатывает `Whitelist`.
- `custom` - применяет regex-правила из textarea.
- `none` - не меняет имена серверов из master subscription.

Формат custom-правил:

```text
regex => replacement
```

Одна строка - одно правило. Пустые строки и строки с `#` в начале игнорируются. Поддерживаются группы `$1`, `$2`, например:

```text
^([A-Z]{2})-\d+.* => $1 custom
^(.+?) → Blanc VPN$ => $1
```

Если ни одно правило не совпало, имя остаётся как в мастер-ссылке. После переименования дубликаты получают `#1`, `#2` и т.д.

`output_format_mode`:

- `auto` - текущая логика: Happ/Throne/FlClash по User-Agent.
- `force_happ` - всегда Happ/base64 URI bundle.
- `force_flclash` - всегда Clash YAML.
- `force_throne` - всегда Throne/base64 URI bundle.

Обычный режим прода - `auto`. Принудительные режимы нужны для отладки или если новая master-ссылка/клиент ведут себя неожиданно.

## Frontend

React/Vite приложение в `apps/web`.

Основные места:

- `src/app/App.tsx` - общий shell, авторизация, выбор разделов.
- `src/app/components/AdminPanel.tsx` - админка: master settings, whitelist, роли, счётчик обновлений.
- `src/app/components/VPNSettings.tsx` - пользовательские VPN-ссылки.
- `src/lib/api.ts` - типы и HTTP client.

В админке whitelist отображается как таблица-карточка с сортировкой по:

- `Email`
- `Кол-во обновлений`
- `Роль`

Сортировка клиентская, по уже загруженному списку.

## Brand assets

Исходники лежат в:

```text
assets/brand/
```

Текущие файлы:

- `logo-light.png`
- `logo-dark.png`
- `app-icon.png`
- `mail-avatar-512.png`
- `source-logo.png`

Фронт импортирует логотипы через alias:

```ts
@brand/logo-light.png
@brand/logo-dark.png
```

Alias настроен в `apps/web/vite.config.ts` и `apps/web/tsconfig.json`.

Иконки сайта генерируются скриптом:

```powershell
python scripts/generate_brand_pngs.py
```

Он берёт `assets/brand/app-icon.png` и пишет favicon/app icons в `apps/web/public`, плюс обновляет `assets/brand/mail-avatar-512.png`.

## Docker / production

На сервере проект лежит в:

```text
~/iter-portal
```

Docker Compose:

```text
docker-compose.yml
```

Сервисы:

- `api` - FastAPI/uvicorn на `0.0.0.0:8000` внутри Docker network.
- `web` - nginx container, раздаёт Vite build и проксирует `/api`, `/config`, `/health`, `/{localpart}/deeplink` на `api:8000`.

Хостовый nginx остаётся снаружи для TLS и проксирует весь домен на локальный порт Docker web:

```text
127.0.0.1:8011
```

Порт задаётся в root `.env`:

```text
ITER_HTTP_PORT=8011
```

Контейнеры имеют:

```yaml
restart: unless-stopped
```

Docker service на сервере включён в автозапуск:

```bash
systemctl is-enabled docker
systemctl is-active docker
```

### Обычный деплой

Локально собрать архив без runtime-мусора, залить, распаковать, пересобрать:

```powershell
tar -czf .\iter-docker-upload.tar.gz `
  --exclude='apps/web/node_modules' `
  --exclude='apps/web/dist' `
  --exclude='apps/api/.venv' `
  --exclude='apps/api/data' `
  --exclude='apps/api/.env' `
  --exclude='apps/api/__pycache__' `
  --exclude='apps/api/.pytest_cache' `
  --exclude='.git' `
  docker-compose.yml .dockerignore .gitignore .env.example apps assets ops scripts

scp .\iter-docker-upload.tar.gz factiosi:~/iter-docker-upload.tar.gz
```

На сервере:

```bash
cd ~/iter-portal
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p ~/iter-backups
cp -a apps/api/data/iter.db ~/iter-backups/iter.db.$TS
tar -xzf ~/iter-docker-upload.tar.gz -C ~/iter-portal --overwrite
docker compose build
docker compose up -d
curl -fsS https://iter.factiosi.com/health
```

После деплоя удалить временный архив:

```bash
rm -f ~/iter-docker-upload.tar.gz
```

### Быстрые проверки прода

```bash
cd ~/iter-portal
docker compose ps
docker compose logs --tail=80 api web
curl -fsS https://iter.factiosi.com/health
```

Проверить конфиг:

```bash
curl -fsS -D - -o /tmp/iter-config-check \
  -H "User-Agent: Happ/3.15.2/Android/1733565" \
  https://iter.factiosi.com/config/<slug>
wc -c /tmp/iter-config-check
```

Проверить БД внутри контейнера:

```bash
docker compose exec -T api python - <<'PY'
import sqlite3
conn = sqlite3.connect("/app/data/iter.db")
print(conn.execute("select owner_email_norm, config_fetch_count from user_main_vpn_links order by id").fetchall())
PY
```

## Local development

Backend:

```powershell
cd apps/api
python -m pip install --user -r requirements.txt -r requirements-dev.txt
python -m pytest
```

Если хочется отдельный venv:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd apps/web
npm install
npm run build
npm run dev
```

В dev Vite проксирует API на `http://127.0.0.1:8010` по умолчанию. Переопределяется через `VITE_API_PROXY`.

## Git / private repo

Проект приватный, лицензия не нужна. В git не должны попадать:

- `.env`
- `apps/api/.env`
- `apps/api/data/`
- `apps/api/.venv/`
- `apps/web/node_modules/`
- `apps/web/dist/`
- временные архивы `*.tar.gz`
- cache/pyc/log/tmp/bak

Перед push:

```powershell
git status --short --ignored
```

Нормально видеть только ignored:

```text
!! apps/api/.env
!! apps/api/data/
```

## История важных решений

- Сначала сайт работал как host nginx -> standalone uvicorn на `127.0.0.1:8010`.
- Потом переведён на Docker: host nginx -> Docker web на `127.0.0.1:8011` -> Docker api.
- Master subscription fetch всегда идёт с Android Happ UA, потому что Blanc master link стабильно отдаёт именно такой формат.
- Happ и Throne получают base64 URI bundle. FlClash получает Clash YAML.
- FlClash deeplink должен быть `clash://install-config?url=<config_url>`, не `flash://`.
- Happ deeplink должен быть `happ://add/<config_url>`.
- `Content-Disposition` для кириллицы делается через ASCII fallback + `filename*=UTF-8''...`, иначе Starlette падает на latin-1.
- `profile-title` отдаётся как `base64:<utf8 title>`, как ожидают клиенты.
- Poisoning не удаляет ссылку сразу: ссылка живёт 31 день или до восстановления whitelist.
