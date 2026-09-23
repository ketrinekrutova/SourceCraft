import { http, HttpResponse } from "msw";
import { myRepositoriesFixture, ratingFixture, repositoryDetailFixture } from "./fixtures";

// Мокает backend/openapi.yaml, пока роутеры бэкенда — заглушки (см. CHECK.md, Этап 0).
// Когда бэкенд будет готов — этот файл просто перестаёт подключаться (см. src/main.tsx),
// компоненты и src/api/client.ts не меняются, потому что форма ответа та же.

let loggedIn = false;

export const handlers = [
  http.get("/api/v1/repositories", ({ request }) => {
    const url = new URL(request.url);
    const language = url.searchParams.get("language");
    const sortBy = url.searchParams.get("sort_by") ?? "health_score";
    const order = url.searchParams.get("order") ?? "desc";

    let items = [...ratingFixture];
    if (language) items = items.filter((r) => r.language === language);

    const key = sortBy === "likes" ? "likes" : sortBy === "last_activity" ? "last_activity_at" : "health_score";
    items.sort((a, b) => {
      const av = a[key as keyof typeof a] ?? 0;
      const bv = b[key as keyof typeof b] ?? 0;
      return av < bv ? -1 : av > bv ? 1 : 0;
    });
    if (order === "desc") items.reverse();

    return HttpResponse.json({ items, page: 1, limit: 20, total: items.length });
  }),

  http.get("/api/v1/repositories/:id", ({ params }) => {
    return HttpResponse.json(repositoryDetailFixture(String(params.id)));
  }),

  http.post("/api/v1/repositories/analyze", async () => {
    return HttpResponse.json(
      { job_id: "job-mock-1", repository_id: "repo-new", status: "IN_PROGRESS", status_url: "/api/v1/jobs/job-mock-1" },
      { status: 202 },
    );
  }),

  http.post("/api/v1/repositories/:id/reanalyze", ({ params }) => {
    return HttpResponse.json(
      { job_id: `job-${params.id}`, repository_id: String(params.id), status: "IN_PROGRESS", status_url: `/api/v1/jobs/job-${params.id}` },
      { status: 202 },
    );
  }),

  // Простой сценарий "идёт анализ...": через ~1.5с job готов — без пошагового прогресса,
  // как договорились (без CLONING/METADATA/... на UI).
  http.get("/api/v1/jobs/:jobId", ({ params }) => {
    return HttpResponse.json({
      job_id: String(params.jobId),
      repository_id: String(params.jobId).replace("job-", "repo-"),
      status: "COMPLETED",
      progress: 1,
    });
  }),

  http.get("/api/v1/repositories/:id/report", ({ params }) => {
    const detail = repositoryDetailFixture(String(params.id));
    const md = `# ${detail.name}\n\n**Repo Health Score:** ${detail.health_score}/100 — ${detail.verdict}\n\n` +
      Object.entries(detail.metrics)
        .map(([key, m]) => `## ${key}\n${m.status === "NO_DATA" ? "Нет данных" : `${m.score}/100 — ${m.summary ?? ""}`}`)
        .join("\n\n");
    return new HttpResponse(md, {
      headers: { "Content-Type": "text/markdown", "Content-Disposition": `attachment; filename="${detail.name}-health.md"` },
    });
  }),

  // Мок-авторизация — вход через Я ID не реализован на бэкенде (v0.3 в openapi.yaml, CHECK.md A2).
  http.post("/api/v1/auth/mock-login", () => {
    loggedIn = true;
    return HttpResponse.json({ display_name: "Тестовый пользователь" });
  }),

  http.get("/api/v1/user/repositories", () => {
    if (!loggedIn) {
      return HttpResponse.json({ error: { code: "UNAUTHORIZED", message: "Требуется вход через Я ID" } }, { status: 401 });
    }
    return HttpResponse.json({ items: myRepositoriesFixture });
  }),
];
