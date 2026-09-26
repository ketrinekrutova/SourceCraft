# Backend

FastAPI + SQLAlchemy (async) + APScheduler. Общая документация, методика и архитектура - в корневом `../README.md`.

```
app/
  clients/        HTTP к SourceCraft API и AppSec (rate limit, повторы), git (shallow-клон, cat-file, blame)
  normalizers/    сырые ответы → Facts (чистые функции)
  scoring/        формулы 6 категорий, агрегатор, рекомендации, engine.evaluate()
  services/       collector (сбор фактов), analysis (задача), queue (очередь в БД), repositories
  workers/        пул воркеров, ночной пересчёт каталога
  routers/        REST API (/api/v1), контракт - openapi.yaml
  reporting/      Markdown-отчёт
  main.py         API (+ воркер и планировщик в процессе, если RUN_WORKER / SCHEDULER_ENABLED)
  worker.py       отдельный процесс-воркер: python -m app.worker
  cli.py          python -m app.cli analyze|discover|sweep|run-queue
tests/            контрольные сценарии методики, нормализаторы, API и контроль доступа
```

```bash
pip install -r requirements.txt -r requirements-dev.txt
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000     # Swagger: http://localhost:8000/api/docs
python -m pytest -q
```
