# Развёртывание

[← К оглавлению документации](README.md)

## Требования

- **Стенд:** Docker 24+ и Docker Compose v2.20+ (нужна поддержка `env_file.required`).
- **Локальная разработка:** Python 3.11+, Node.js 20+, git в `PATH`.
- **Доступы:** PAT команды SourceCraft (желательно), OAuth-приложение Я ID (для входа пользователей).

## 1. Подготовка конфигурации

```bash
cp .env.example .env
```

| Переменная | Обязательна | По умолчанию | Назначение |
|---|---|---|---|
| `SOURCECRAFT_SERVICE_PAT` | желательно | пусто | PAT команды для каталога `GET /repos` и публичных данных API (CI/CD, Issues). Без него каталог берётся с открытой страницы, анализ идёт только по git |
| `YA_ID_CLIENT_ID`, `YA_ID_CLIENT_SECRET` | для входа | пусто | OAuth-приложение Я ID |
| `YA_ID_REDIRECT_URI` | для входа | `http://localhost:8080/api/v1/auth/yandex/callback` | должен совпадать с Callback URI в настройках приложения |
| `FRONTEND_URL` | да | `http://localhost:8080` | куда вернуть пользователя после входа |
| `SECRET_KEY` | **да** | `change-me` | подпись сессий и шифрование PAT. Сгенерировать: `openssl rand -hex 32`. После смены сохранённые PAT перестают расшифровываться |
| `COOKIE_SECURE` | для HTTPS | `false` | `true` за HTTPS |
| `CORS_ORIGINS` | нет | `http://localhost:8080` | нужен, только если фронтенд на другом origin |
| `DEV_LOGIN_ENABLED` | нет | `false` | вход без Я ID для локальной проверки. **В продакшене - `false`** |
| `SOURCECRAFT_API_RPS` | нет | `8` | лимит запросов к SourceCraft на процесс (лимит платформы 10 rps на хост) |
| `APPSEC_API_RPS` | нет | `50` | лимит к AppSec на процесс (лимит платформы 100 rps) |
| `SCHEDULE_CRON` | нет | `0 3 * * *` | расписание обхода каталога, UTC |
| `RECALC_INTERVAL_HOURS` | нет | `24` | минимальный интервал между пересчётами репозитория |
| `WORKER_CONCURRENCY` | нет | `2` | параллельных анализов в одном процессе-воркере |

Дополнительные параметры (границы анализа крупных репозиториев, таймауты, `DATABASE_URL`, `WORK_DIR`, `DISCOVERY_MAX_REPOS`) - в `backend/app/config.py`; любое поле задаётся переменной окружения с тем же именем в верхнем регистре.

### Регистрация приложения Я ID

1. <https://oauth.yandex.ru/client/new> → платформа «Веб-сервисы».
2. Redirect URI: `<адрес стенда>/api/v1/auth/yandex/callback` (локально - `http://localhost:8080/api/v1/auth/yandex/callback`).
3. Доступы: логин, имя и аватар пользователя.
4. ClientID и Client secret - в `YA_ID_CLIENT_ID` / `YA_ID_CLIENT_SECRET`.

## 2. Запуск стенда (Docker Compose)

```bash
docker compose up -d --build
docker compose ps                      # db healthy, api/worker/web running
curl http://localhost:8080/api/v1/repositories?limit=1
```

- Интерфейс: <http://localhost:8080>
- Swagger: <http://localhost:8080/api/docs>

При первом старте с пустой базой автоматически запускается обход каталога и все репозитории ставятся в очередь. Полный первичный расчёт (~28 тыс. репозиториев) занимает часы; до его завершения нерассчитанные репозитории стоят в конце рейтинга с пометкой «ожидает анализа».

### Масштабирование воркеров

```bash
docker compose up -d --scale worker=3
```

Лимит частоты действует на процесс, поэтому при N процессах (воркеры + api) задайте `SOURCECRAFT_API_RPS ≈ 10 / N`, например `2.5` при трёх воркерах.

### Обновление

```bash
git pull
docker compose up -d --build           # данные в томе pgdata сохраняются
```

## 3. Публикация в интернет

Compose публикует только `web` на порту `8080`. Для боевого стенда:

1. Поставьте перед `web` TLS-терминатор (внешний nginx, Caddy, балансировщик Yandex Cloud) и проксируйте на `:8080`, передавая `X-Forwarded-Proto`.
2. В `.env`: `FRONTEND_URL=https://<домен>`, `YA_ID_REDIRECT_URI=https://<домен>/api/v1/auth/yandex/callback`, `CORS_ORIGINS=https://<домен>`, `COOKIE_SECURE=true`, свой `SECRET_KEY`, `DEV_LOGIN_ENABLED=false`.
3. Смените пароль Postgres в `docker-compose.yml` (сервис `db` и `DATABASE_URL` у `api`/`worker`) или вынесите БД в управляемый PostgreSQL, указав `DATABASE_URL=postgresql+asyncpg://…`.

## 4. Локальный запуск без Docker

```bash
# backend: API + воркер + планировщик в одном процессе, SQLite
cd backend
python -m venv .venv
.venv/Scripts/activate                  # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp ../.env.example .env                 # DEV_LOGIN_ENABLED=true, FRONTEND_URL=http://localhost:5173
uvicorn app.main:app --port 8000        # Swagger: http://localhost:8000/api/docs

# frontend (в другом терминале), /api проксируется на :8000
cd frontend
npm ci
npm run dev                             # http://localhost:5173
```

## 5. Проверка и эксплуатация

```bash
cd backend
python -m pytest -q                                   # тесты методики, нормализаторов, API
python -m app.cli analyze <org>/<repo>                # анализ одного репозитория в консоли
python -m app.cli sweep                               # то же, что ночное расписание
python -m app.cli run-queue                           # выполнить очередь и выйти
```

| Задача | Команда |
|---|---|
| Проверка живости API | `GET /health` → `{"status": "ok"}` |
| Логи | `docker compose logs -f api worker` |
| Резервная копия БД | `docker compose exec db pg_dump -U repo_health repo_health > backup.sql` |
| Восстановление | `docker compose exec -T db psql -U repo_health repo_health < backup.sql` |
| Полный сброс данных | `docker compose down -v` (удаляет том `pgdata`) |

## Частые проблемы

| Симптом | Причина и решение |
|---|---|
| CI/CD и Issues везде «Нет данных» | не задан `SOURCECRAFT_SERVICE_PAT` или у токена нет прав на чужие репозитории - ожидаемое поведение |
| Ошибка входа через Я ID / redirect_uri mismatch | `YA_ID_REDIRECT_URI` не совпадает с Callback URI приложения |
| Сессия не сохраняется | `COOKIE_SECURE=true` при доступе по HTTP, либо фронтенд и API на разных origin |
| Сохранённые PAT перестали работать | сменился `SECRET_KEY` - пользователям нужно ввести PAT заново |
| 429 от SourceCraft, медленный обход | сумма `SOURCECRAFT_API_RPS` по процессам превышает 10 - уменьшите значение |
| `PDF_FONT_MISSING` при выгрузке PDF | вне Docker не установлен шрифт DejaVu (`fonts-dejavu-core`) |
