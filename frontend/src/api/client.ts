import type {
  AuthState,
  HistoryPoint,
  Job,
  JobAccepted,
  Me,
  RepositoryDetail,
  RepositoryPage,
  Scope,
  UserRepositoryList,
} from "./types";

// Бэкенд на том же origin: в разработке через proxy Vite, в продакшене через nginx.
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.error?.code ?? "ERROR", body?.error?.message ?? `Ошибка запроса: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
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
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return request<RepositoryPage>(`/repositories${qs ? `?${qs}` : ""}`);
}

export const fetchLanguages = () => request<string[]>("/repositories/languages");

const enc = encodeURIComponent;

export const fetchRepository = (id: string, scope: Scope) =>
  request<RepositoryDetail>(`/repositories/${enc(id)}?scope=${scope}`);

export const fetchHistory = (id: string, scope: Scope) =>
  request<HistoryPoint[]>(`/repositories/${enc(id)}/history?scope=${scope}`);

export const analyzeRepository = (repositoryUrl: string, scope: Scope) =>
  request<JobAccepted>("/repositories/analyze", {
    method: "POST",
    body: JSON.stringify({ repository_url: repositoryUrl, scope }),
  });

export const reanalyzeRepository = (id: string, scope: Scope) =>
  request<JobAccepted>(`/repositories/${enc(id)}/reanalyze?scope=${scope}`, { method: "POST" });

export const fetchJob = (jobId: string) => request<Job>(`/jobs/${enc(jobId)}`);

export const reportDownloadUrl = (id: string, scope: Scope, format: "markdown" | "pdf" = "markdown") =>
  `${API_BASE}/repositories/${enc(id)}/report?format=${format}&scope=${scope}`;

// --- авторизация и личный кабинет ---

export const fetchAuth = () => request<AuthState>("/auth/me");
export const yandexLoginUrl = () => `${API_BASE}/auth/yandex/login`;
export const devLogin = () => request<AuthState>("/auth/dev-login", { method: "POST" });
export const logout = () => request<void>("/auth/logout", { method: "POST" });

export const saveToken = (token: string) => request<Me>("/user/token", { method: "PUT", body: JSON.stringify({ token }) });
export const deleteToken = () => request<Me>("/user/token", { method: "DELETE" });
export const saveOrgs = (orgs: string[]) => request<Me>("/user/orgs", { method: "PUT", body: JSON.stringify({ orgs }) });
export const fetchMyRepositories = () => request<UserRepositoryList>("/user/repositories");
