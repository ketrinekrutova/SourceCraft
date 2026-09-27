# Архитектура

[← К оглавлению документации](README.md)

## Компоненты

```
                    ┌──────────────────────────── Docker Compose ────────────────────────────┐
 Браузер ──HTTP──▶  │ web (nginx)                                                            │
                    │   /        → SPA (React, собранный dist/)                              │
                    │   /api/*   → api:8000                                                  │
                    │                                                                        │
                    │ api (FastAPI + APScheduler)        worker ×N (python -m app.worker)    │
                    │   REST /api/v1, Я ID OAuth,          забирают задачи из очереди,        │
                    │   постановка задач, ночной обход     собирают факты, считают Score      │
                    │            │                                   │                       │
                    │            └──────────── db (PostgreSQL) ──────┘                       │
                    └───────────────────────────────────────────────────────────────────────┘
                                                        │
                    api.sourcecraft.tech · appsec.sourcecraft.tech · git.sourcecraft.dev · oauth.yandex.ru
```

| Сервис | Образ / команда | Роль |
|---|---|---|
| `web` | `frontend/Dockerfile` → nginx | отдаёт SPA и проксирует `/api/` на `api`; SPA и API на одном origin, поэтому cookie сессии работает без CORS |
| `api` | `backend/Dockerfile` → `uvicorn app.main:app` | REST API, OAuth Я ID, постановка задач, планировщик (`SCHEDULER_ENABLED=true`, `RUN_WORKER=false`) |
| `worker` | тот же образ → `python -m app.worker` | выполнение анализов; масштабируется `--scale worker=N` |
| `db` | `postgres:16-alpine` | репозитории, история анализов, очередь задач, пользователи |

При локальном запуске (`uvicorn app.main:app`) API, воркер и планировщик работают в одном процессе на SQLite.

## Слои backend

```
routers/  ──▶  services/  ──▶  clients/      (I/O: SourceCraft API, AppSec, каталог, git)
                   │
                   ├──▶  normalizers/   сырые ответы → Facts (чистые функции)
                   └──▶  scoring/       Facts → категории, Score, рекомендации (без I/O)
                            reporting/  результат → Markdown / PDF
```

| Модуль | Файлы | Ответственность |
|---|---|---|
| Клиенты | `app/clients/` | `sourcecraft_api.py` - REST SourceCraft; `scs_security.py` - AppSec; `sourcecraft_web.py` - каталог через открытую страницу (без PAT); `git_client.py` - shallow-клон, `cat-file --batch`, `blame`; `http.py` - лимит частоты на хост, повторы на 429/5xx, классификация отказов (`no_access`, `not_found`, `unavailable`) |
| Нормализаторы | `app/normalizers/` | по модулю на категорию; превращают ответы источников в `Facts` (`app/scoring/facts.py`) |
| Скоринг | `app/scoring/` | `categories/*.py` - формулы; `aggregate.py` - взвешивание и перенормировка; `recommendations.py` - правила и расчёт эффекта; `engine.evaluate()` - точка входа |
| Сервисы | `app/services/` | `collector.py` - сбор фактов по этапам; `analysis.py` - выполнение задачи и сохранение; `queue.py` - очередь в БД; `repositories.py` - каталог и разрешение ссылок; `serialize.py` - результат в JSON |
| Воркеры | `app/workers/` | `worker.py` - пул с heartbeat; `scheduler.py` - ночной обход каталога |
| API | `app/routers/` | см. [API.md](API.md) |
| Отчёты | `app/reporting/` | Markdown и PDF (шрифт DejaVu для кириллицы) |
| CLI | `app/cli.py` | `analyze`, `discover`, `sweep`, `run-queue` - воспроизведение без UI |

## Поток анализа

```
POST /repositories/analyze ──▶ jobs (PENDING) ──▶ worker: SELECT … FOR UPDATE SKIP LOCKED
                                                        │
      METADATA ─▶ CLONING ─▶ CODE_SCAN ─▶ SECURITY_SCAN ─▶ SCORING
      (API:       (shallow    (дерево, README,  (AppSec,       (engine.evaluate:
       repo, CI,   clone,      TODO, blame)      только личный   категории, Score,
       issues, MR) 181 день)                     анализ)         рекомендации)
                                                        │
                           analyses.result_json ◀───────┘  (+ денормализация Score в repositories для публичного)
                                                        │
      фронтенд опрашивает GET /jobs/{id} раз в 2 с ──▶ GET /repositories/{id}
```

1. **Постановка.** Запрос возвращает `202` и `job_id`. Постановка идемпотентна: пока по репозиторию есть задача в `PENDING`/`IN_PROGRESS`, возвращается она.
2. **Приоритеты.** Меньше - раньше: личный запуск 10, ручной публичный 50, расписание 100.
3. **Выполнение.** Воркер захватывает задачу, пишет `stage`/`progress` и `heartbeat_at`. Отказ отдельного источника не роняет анализ: категория получает «Нет данных» с причиной, задача завершается статусом `PARTIAL`.
4. **Сохранение.** Результат целиком пишется в `analyses.result_json`; страница, история и отчёты строятся из этой записи. Для публичного анализа Score копируется в `repositories.health_score` (рейтинг - один индексированный запрос).
5. **Сбои.** Задача без heartbeat дольше `JOB_STALE_AFTER_S` возвращается в очередь (до 3 попыток). При `FAILED` предыдущий результат остаётся, интерфейс показывает «анализ не обновлён».

## Модель данных

```
users 1──* user_repo_access *──1 repositories 1──* analyses
  │                                   │
  └──────────────* jobs *─────────────┘
```

| Таблица | Назначение | Ключевые поля |
|---|---|---|
| `repositories` | каталог (id - Repository.id SourceCraft, его же принимает AppSec) | `org_slug`, `slug`, `visibility`, `language`, `likes`, `in_catalog`; денормализованные `health_score`, `coverage`, `last_analyzed_at`, `analysis_status` - только публичные |
| `analyses` | история анализов | `owner_user_id` (NULL - публичный, иначе личный), `status` (COMPLETED/PARTIAL), `health_score`, `methodology_version`, `result_json` |
| `jobs` | очередь | `trigger` (schedule/manual/user), `priority`, `status`, `stage`, `progress`, `heartbeat_at`, `worker_id`, `attempts`, `error_code` |
| `users` | вход через Я ID | `yandex_id`, `sc_token_encrypted` (PAT, Fernet), `sc_username`, `sc_orgs_json` |
| `user_repo_access` | подтверждённый доступ PAT к репозиторию | `verified_at` - перепроверяется у SourceCraft, если старше часа |

Схема создаётся `create_all` при старте. Для изменений схемы на рабочем стенде понадобятся миграции (Alembic).

## Периодический пересчёт

`app/workers/scheduler.py`, cron `SCHEDULE_CRON` (по умолчанию `0 3 * * *` UTC):

1. Обход каталога: `GET /repos` с сервисным PAT или открытая страница «Топ репозиториев» без него. Пропавшие из каталога репозитории помечаются `in_catalog=false`.
2. В очередь ставятся репозитории, чей публичный анализ старше `RECALC_INTERVAL_HOURS`; сначала ещё не анализированные.

При пустой базе обход запускается сразу при старте.

## Безопасность и разделение данных

- **Сессия** - подписанная httpOnly-cookie (`SECRET_KEY`, `itsdangerous`); OAuth-токен Яндекса не сохраняется.
- **PAT пользователя** проверяется `GET /user` и хранится только зашифрованным (Fernet, ключ из `SECRET_KEY`). Удаление PAT снимает все подтверждения доступа.
- **Личный анализ** выполняется только с PAT пользователя; сервисный токен для чужих данных не используется.
- **Закрытые данные** отдаются только при записи в `user_repo_access`; при отзыве доступа закрывается и уже готовый отчёт.
- **Публичный рейтинг** строится только по публичным репозиториям и публичным анализам (без AppSec). Личные результаты туда не попадают.
- **Код репозиториев** клонируется во временный каталог и удаляется в `finally` сразу после анализа.
- **Лимиты.** Исходящие запросы ограничены на хост (`SOURCECRAFT_API_RPS`, `APPSEC_API_RPS`); ручные запуски анализа - 20 за 10 минут с одного IP.

## Frontend

`frontend/src/`:

| Путь | Назначение |
|---|---|
| `pages/RatingPage.tsx` | `/` - рейтинг: сортировка, фильтр по языку, пагинация, запуск анализа по ссылке |
| `pages/AnalysisPage.tsx` | `/repositories/:id` (`?scope=personal` - личный) - Score, категории, факты, рекомендации, история, отчёты |
| `pages/MyRepositoriesPage.tsx` | `/my-repositories` - PAT, организации, список доступных репозиториев |
| `api/client.ts`, `api/hooks.ts`, `api/types.ts` | HTTP-клиент, хуки TanStack Query (опрос задачи раз в 2 с), типы - зеркало `openapi.yaml` |
| `auth/AuthContext.tsx` | текущий пользователь (`/auth/me`) |
