# Документация SourceCraft Repo Health

Пояснительная записка к решению кейса №8 Yandex Cloud («Лидеры цифровой трансформации 2026»): веб-сервис, который считает **Repo Health Score (0-100)** для репозиториев SourceCraft, объясняет оценку и даёт рекомендации с подтверждающими фактами.

| Документ | Содержание |
|---|---|
| [Архитектура](ARCHITECTURE.md) | компоненты, поток анализа, модель данных, очередь и воркеры, безопасность |
| [Развёртывание](DEPLOYMENT.md) | Docker Compose, локальный запуск, переменные окружения, Я ID, масштабирование, эксплуатация |
| [API](API.md) | REST API `/api/v1`: эндпоинты, параметры, коды ошибок, примеры |
| [Методика Score и ограничения](../README.md#методика-repo-health-score) | формулы шести категорий, «Нет данных», рекомендации, крупные репозитории |
| [OpenAPI-контракт](../backend/openapi.yaml) | машиночитаемая спецификация; живой Swagger - `/api/docs` |

## Кратко

- **Что делает.** Публичный рейтинг всего каталога открытых репозиториев SourceCraft (~28 тыс.) и личный анализ своих репозиториев (включая приватные, с данными AppSec) после входа через Я ID.
- **Как оценивает.** Шесть категорий: Security 20, Code health 20, Activity 15, Documentation 15, CI/CD 15, Issues 15. Категории без данных исключаются с перенормировкой весов, а не обнуляются.
- **Откуда данные.** SourceCraft API, AppSec API, git SourceCraft (shallow-клон), Я ID. LLM и сторонние AI-сервисы не используются.
- **Как работает.** Анализ асинхронный: API ставит задачу в очередь в БД, воркеры (масштабируются горизонтально) собирают факты, считают Score и сохраняют результат целиком; ночной планировщик пересчитывает каталог.

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2 (async), Pydantic Settings, APScheduler 3, httpx, git CLI, fpdf2, cryptography (Fernet), itsdangerous (подпись сессий) |
| База данных | PostgreSQL 16 (стенд), SQLite (локальный запуск) |
| Frontend | React 19, TypeScript, Vite, React Router 7, TanStack Query 5, CSS Modules |
| Инфраструктура | Docker, Docker Compose, nginx (SPA + reverse proxy `/api`) |
| Тесты | pytest: контрольные сценарии методики, нормализаторы, API и контроль доступа |

## Быстрый старт

```bash
cp .env.example .env          # SOURCECRAFT_SERVICE_PAT, YA_ID_*, SECRET_KEY
docker compose up -d --build  # http://localhost:8080, Swagger - http://localhost:8080/api/docs
```

Подробно - в [DEPLOYMENT.md](DEPLOYMENT.md).
