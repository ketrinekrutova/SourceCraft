import type { JobAccepted, RepositoryDetail, RepositoryPage, UserRepository } from "./types";

// Один общий базовый адрес. Пока бэкенд не готов, запросы перехватывает MSW (src/mocks/handlers.ts).
// Когда появится реальный бэкенд — здесь меняется только эта строка (или .env), компоненты не трогаем.
const API_BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `Request failed: ${res.status}`);
  }
  if (res.status === 202 || res.status === 204) {
    return res.json().catch(() => undefined) as Promise<T>;
  }
  return res.json();
}

export interface RatingQuery {
  language?: string;
  sort_by?: "health_score" | "likes" | "last_activity";
  order?: "asc" | "desc";
  page?: number;
  limit?: number;
}

export function fetchRating(query: RatingQuery): Promise<RepositoryPage> {
  const params = new URLSearchParams();
  if (query.language) params.set("language", query.language);
  if (query.sort_by) params.set("sort_by", query.sort_by);
  if (query.order) params.set("order", query.order);
  if (query.page) params.set("page", String(query.page));
  if (query.limit) params.set("limit", String(query.limit));
  const qs = params.toString();
  return request<RepositoryPage>(`/repositories${qs ? `?${qs}` : ""}`);
}

export function fetchRepository(id: string): Promise<RepositoryDetail> {
  return request<RepositoryDetail>(`/repositories/${id}`);
}

export function analyzeRepository(repositoryUrl: string): Promise<JobAccepted> {
  return request<JobAccepted>("/repositories/analyze", {
    method: "POST",
    body: JSON.stringify({ repository_url: repositoryUrl }),
  });
}

export function reanalyzeRepository(id: string): Promise<JobAccepted> {
  return request<JobAccepted>(`/repositories/${id}/reanalyze`, { method: "POST" });
}

export function fetchJob(jobId: string) {
  return request(`/jobs/${jobId}`);
}

export function reportDownloadUrl(id: string, format: "markdown" | "pdf" = "markdown"): string {
  return `${API_BASE}/repositories/${id}/report?format=${format}`;
}

// v0.3 в openapi.yaml (авторизация ещё не в контракте бэкенда) — мокаем целиком на фронте,
// см. src/mocks/handlers.ts и src/auth/AuthContext.tsx.
export function fetchMyRepositories(): Promise<{ items: UserRepository[] }> {
  return request<{ items: UserRepository[] }>("/user/repositories");
}

export function mockLogin(): Promise<{ display_name: string }> {
  return request<{ display_name: string }>("/auth/mock-login", { method: "POST" });
}
