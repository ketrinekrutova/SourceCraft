# Frontend

React 19 + TypeScript + Vite + TanStack Query. Страницы: рейтинг (`/`), анализ репозитория (`/repositories/:id`, `?scope=personal` - личный анализ), «Мои репозитории» (`/my-repositories`).

```bash
npm ci
npm run dev      # http://localhost:5173, /api проксируется на http://localhost:8000 (VITE_API_PROXY)
npm run build    # dist/ - в продакшене отдаётся nginx (nginx.conf), /api проксируется на бэкенд
```

Типы ответов API - `src/api/types.ts` (зеркало `backend/openapi.yaml`). Сессия - httpOnly-cookie бэкенда, фронтенд и API всегда на одном origin.
