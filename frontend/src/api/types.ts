// Зеркало ответов бэкенда (backend/openapi.yaml, backend/app/schemas). Новые поля сначала
// появляются в openapi.yaml и схемах бэкенда, потом здесь.

export type AnalysisStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "PARTIAL" | "FAILED";
export type MetricStatus = "OK" | "NO_DATA";
export type Priority = "HIGH" | "MEDIUM" | "LOW";
export type EvidenceType = "file" | "pipeline" | "vulnerability" | "commit" | "issue" | "merge_request";
export type Scope = "public" | "personal";

export type CategoryKey = "documentation" | "ci_cd" | "security" | "activity" | "issues" | "code_health";

export interface RepositorySummary {
  id: string;
  name: string;
  full_name: string;
  url: string;
  health_score: number | null;
  likes: number;
  language: string | null;
  last_activity_at: string | null;
  last_analyzed_at: string | null;
  status: AnalysisStatus;
  coverage: number | null;
}

export interface RepositoryPage {
  items: RepositorySummary[];
  page: number;
  limit: number;
  total: number;
  summary: { catalog_total: number; analyzed_total: number; last_analyzed_at: string | null };
}

export interface Evidence {
  type: EvidenceType;
  ref: string;
  url?: string | null;
}

export interface Component {
  label: string;
  points: number | null;
  max_points: number;
  value: string;
}

export interface Metric {
  score: number | null;
  status: MetricStatus;
  summary?: string | null;
  weight: number;
  base_weight: number;
  contribution: number;
  components: Component[];
  details: Record<string, unknown>;
  evidence: Evidence[];
}

export type Metrics = Record<CategoryKey, Metric>;

export interface Recommendation {
  id: string;
  priority: Priority;
  category: CategoryKey;
  title: string;
  description: string;
  problem: string;
  why_it_matters: string;
  action: string;
  facts: string;
  impact?: string | null;
  score_gain: number;
  evidence: Evidence[];
}

export interface JobInfo {
  job_id: string;
  status: AnalysisStatus;
  stage?: string | null;
  progress: number;
  created_at?: string | null;
  finished_at?: string | null;
  error?: { code: string | null; message: string | null } | null;
}

export interface RepositoryDetail {
  id: string;
  name: string;
  full_name: string;
  url: string;
  description: string | null;
  language: string | null;
  likes: number;
  visibility: string;
  scope: Scope;
  health_score: number | null;
  verdict: string;
  status: AnalysisStatus;
  last_analyzed_at: string | null;
  methodology_version: string | null;
  coverage: number;
  metrics: Metrics | null;
  strengths: string[];
  weaknesses: string[];
  recommendations: Recommendation[];
  sources: Record<string, string>;
  previous: { health_score: number | null; analyzed_at: string } | null;
  latest_job: JobInfo | null;
}

export interface HistoryPoint {
  analyzed_at: string;
  health_score: number | null;
  status: AnalysisStatus;
}

export interface UserRepository {
  id: string;
  name: string;
  full_name: string;
  url: string;
  private: boolean;
  visibility: string;
  health_score: number | null;
  likes: number;
  language: string | null;
  last_activity_at: string | null;
  last_analyzed_at: string | null;
  analyzed: boolean;
}

export interface UserRepositoryList {
  items: UserRepository[];
  orgs_checked: string[];
  errors: string[];
}

export interface Me {
  id: string;
  login: string | null;
  display_name: string | null;
  avatar_url: string | null;
  has_token: boolean;
  sourcecraft_username: string | null;
  orgs: string[];
}

export interface AuthState {
  authenticated: boolean;
  user: Me | null;
  yandex_id_configured: boolean;
  dev_login_enabled: boolean;
}

export interface JobAccepted {
  job_id: string;
  repository_id: string;
  status: AnalysisStatus;
  queued_at?: string;
  status_url: string;
  scope: Scope;
}

export interface Job {
  job_id: string;
  repository_id: string;
  status: AnalysisStatus;
  progress: number;
  stage?: "CLONING" | "METADATA" | "SECURITY_SCAN" | "CODE_SCAN" | "SCORING" | null;
  started_at?: string | null;
  finished_at?: string | null;
  error?: { code: string | null; message: string | null } | null;
  scope: Scope;
}

export const CATEGORY_ORDER: CategoryKey[] = ["documentation", "ci_cd", "security", "activity", "issues", "code_health"];

export const CATEGORY_LABELS: Record<CategoryKey, string> = {
  documentation: "Documentation",
  ci_cd: "CI/CD",
  security: "Security",
  activity: "Activity",
  issues: "Issues",
  code_health: "Code health",
};

export const STAGE_LABELS: Record<string, string> = {
  METADATA: "Сбор данных из SourceCraft API",
  CLONING: "Получение git-истории",
  CODE_SCAN: "Анализ кода и истории",
  SECURITY_SCAN: "Результаты AppSec",
  SCORING: "Расчёт Score",
};

export function isActive(status: AnalysisStatus | undefined | null): boolean {
  return status === "PENDING" || status === "IN_PROGRESS";
}
