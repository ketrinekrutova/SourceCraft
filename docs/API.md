# API

[← К оглавлению документации](README.md)

Базовый путь - `/api/v1`. Машиночитаемый контракт - [`backend/openapi.yaml`](../backend/openapi.yaml), интерактивный Swagger - `/api/docs` на запущенном стенде.

## Общие правила

- **Формат** - JSON, даты в ISO 8601 (UTC).
- **Аутентификация** - httpOnly-cookie сессии после входа через Я ID. Публичные эндпоинты доступны без входа.
- **`scope`** - `public` (по умолчанию): публичный анализ, как в рейтинге; `personal`: личный анализ по PAT пользователя, включая AppSec, виден только ему.
- **Анализ асинхронный:** запуск возвращает `202` и `job_id`, статус - `GET /jobs/{job_id}`.
- **Ошибки:** `{"error": {"code": "REPOSITORY_NOT_FOUND", "message": "…"}}`.

## Эндпоинты

### Рейтинг

| Метод | Путь | Описание |
|---|---|---|
| GET | `/repositories` | публичный рейтинг. Параметры: `sort_by` = `health_score` \| `likes` \| `last_activity` (по умолчанию `health_score`), `order` = `desc` \| `asc`, `language`, `page` (≥1), `limit` (1-100, по умолчанию 20). Ответ: `items`, `page`, `limit`, `total`, `summary` (`catalog_total`, `analyzed_total`, `last_analyzed_at`) |
| GET | `/repositories/languages` | список языков для фильтра |

### Анализ

| Метод | Путь | Описание |
|---|---|---|
| POST | `/repositories/analyze` | запуск анализа по ссылке. Тело: `{"repository_url": "https://sourcecraft.dev/org/repo", "scope": "public"}` (принимается и `org/repo`). `202` + `JobAccepted` |
| POST | `/repositories/{repo_id}/reanalyze?scope=` | повторный анализ. `202` + `JobAccepted` |
| GET | `/jobs/{job_id}` | статус задачи: `status` (PENDING, IN_PROGRESS, COMPLETED, PARTIAL, FAILED), `stage` (METADATA, CLONING, CODE_SCAN, SECURITY_SCAN, SCORING), `progress` 0-1, `error` |
| GET | `/repositories/{repo_id}?scope=` | полный отчёт: `health_score`, `verdict`, `coverage`, `metrics` (6 категорий с `score`, `status`, `weight`, `base_weight`, `contribution`, `components`, `evidence`), `strengths`, `weaknesses`, `recommendations`, `sources`, `previous`, `latest_job` |
| GET | `/repositories/{repo_id}/history?scope=` | до 30 последних анализов: `analyzed_at`, `health_score`, `status` |
| GET | `/repositories/{repo_id}/report?format=markdown\|pdf&scope=` | отчёт файлом (`Content-Disposition: attachment`) из последнего завершённого анализа |

Запуски идемпотентны: пока по репозиторию есть незавершённая задача, возвращается она. Лимит - 20 запусков за 10 минут с одного IP.

### Авторизация

| Метод | Путь | Описание |
|---|---|---|
| GET | `/auth/yandex/login` | редирект на OAuth Я ID |
| GET | `/auth/yandex/callback` | обработка ответа Я ID, установка cookie, редирект на `FRONTEND_URL` |
| POST | `/auth/dev-login` | вход без Я ID, только при `DEV_LOGIN_ENABLED=true` |
| GET | `/auth/me` | `authenticated`, `user` (или `null`), `yandex_id_configured`, `dev_login_enabled` |
| POST | `/auth/logout` | выход, `204` |

### Личный кабинет (требует входа)

| Метод | Путь | Описание |
|---|---|---|
| PUT | `/user/token` | сохранить PAT SourceCraft: `{"token": "…"}`. Токен проверяется `GET /user` и хранится зашифрованным. Ответ - `Me` |
| DELETE | `/user/token` | удалить PAT и все подтверждения доступа |
| PUT | `/user/orgs` | организации для «Моих репозиториев»: `{"orgs": ["my-org"]}` |
| GET | `/user/repositories` | доступные репозитории: личное пространство, указанные организации и добавленные по ссылке. Ответ: `items`, `orgs_checked`, `errors` |

### Служебные

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | проверка живости (без префикса `/api/v1`) |
| GET | `/api/docs` | Swagger UI |

## Коды ошибок

| HTTP | `code` | Когда |
|---|---|---|
| 400 | `BAD_REQUEST` | ошибка валидации параметров или тела |
| 400 | `INVALID_SCOPE` | `scope` не `public` / `personal` |
| 400 | `INVALID_SORT` | неизвестный `sort_by` / `order` |
| 400 | `INVALID_REPOSITORY_URL` | ссылка не распознана как `org/repo` |
| 400 | `UNSUPPORTED_FORMAT` | формат отчёта не `markdown` / `pdf` |
| 400 | `NO_TOKEN` | личный анализ без сохранённого PAT |
| 401 | `UNAUTHORIZED` | требуется вход через Я ID |
| 403 | `NO_TOKEN` / `ACCESS_DENIED` | нет PAT или PAT больше не даёт доступа к репозиторию |
| 404 | `REPOSITORY_NOT_FOUND` | репозитория нет или нет доступа |
| 409 | `NO_ANALYSIS` | отчёт запрошен до первого завершённого анализа |
| 429 | `RATE_LIMIT_EXCEEDED` | превышен лимит запусков анализа |
| 500 | `PDF_FONT_MISSING` | в окружении нет шрифта для PDF |
| 502 | `SOURCECRAFT_UNAVAILABLE` | SourceCraft API не ответил |

## Пример: анализ репозитория

```bash
# 1. Запуск
curl -s -X POST http://localhost:8080/api/v1/repositories/analyze \
  -H 'Content-Type: application/json' \
  -d '{"repository_url": "https://sourcecraft.dev/aladin/showcase-math-whiz"}'
# 202 {"job_id": "…", "repository_id": "…", "status": "PENDING", "status_url": "/api/v1/jobs/…", "scope": "public", …}

# 2. Опрос статуса, пока status не COMPLETED / PARTIAL / FAILED
curl -s http://localhost:8080/api/v1/jobs/<job_id>
# {"job_id": "…", "status": "IN_PROGRESS", "stage": "CODE_SCAN", "progress": 0.6, …}

# 3. Результат и отчёт
curl -s http://localhost:8080/api/v1/repositories/<repository_id>
curl -s -OJ "http://localhost:8080/api/v1/repositories/<repository_id>/report?format=pdf"
```

## Обновление `openapi.yaml`

Файл генерируется из кода:

```bash
cd backend
python -c "import yaml; from app.main import app; yaml.safe_dump(app.openapi(), open('openapi.yaml', 'w', encoding='utf-8'), allow_unicode=True, sort_keys=False)"
```
