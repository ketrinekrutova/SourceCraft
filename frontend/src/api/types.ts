// Зеркало backend/openapi.yaml. Не придумывать новые поля здесь — если чего-то не хватает,
// сначала дописать в openapi.yaml (см. пример в README/CHECK.md обсуждения verdict/missing_data).

export type AnalysisStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "PARTIAL" | "FAILED";
export type MetricStatus = "OK" | "NO_DATA";
export type Priority = "HIGH" | "MEDIUM" | "LOW";
export type EvidenceType = "file" | "pipeline" | "vulnerability" | "commit" | "issue" | "merge_request";

export type CategoryKey =
  | "documentation"
  | "ci_cd"
  | "security"
  | "activity"
  | "issues"
  | "code_health";

export interface RepositorySummary {
  id: string;
  name: string;
  url: string;
  health_score: number | null;
  likes: number;
  language: string | null;
  last_activity_at: string | null;
  last_analyzed_at: string | null;
  status: AnalysisStatus;
}

export interface RepositoryPage {
  items: RepositorySummary[];
  page: number;
  limit: number;
  total: number;
}

export interface Evidence {
  type: EvidenceType;
  ref: string;
  url?: string | null;
}

export interface Metric {
  score: number | null;
  status: MetricStatus;
  summary?: string | null;
  weight: number;
  details: Record<string, unknown>;
}

export interface Metrics {
  documentation: Metric;
  ci_cd: Metric;
  security: Metric;
  activity: Metric;
  issues: Metric;
  code_health: Metric;
}

export interface Recommendation {
  id: string;
  priority: Priority;
  category: CategoryKey;
  title: string;
  description: string;
  impact?: string | null;
  evidence: Evidence[];
}

export interface RepositoryDetail {
  id: string;
  name: string;
  url: string;
  language: string | null;
  health_score: number | null;
  verdict: string;
  status: AnalysisStatus;
  last_analyzed_at: string | null;
  metrics: Metrics;
  recommendations: Recommendation[];
}

export interface UserRepository {
  id: string;
  name: string;
  private: boolean;
  health_score: number | null;
  likes: number;
  language: string | null;
  last_activity_at: string | null;
}

export interface JobAccepted {
  job_id: string;
  repository_id: string;
  status: AnalysisStatus;
  queued_at?: string;
  status_url: string;
}

export interface Job {
  job_id: string;
  repository_id: string;
  status: AnalysisStatus;
  progress?: number;
  stage?: "CLONING" | "METADATA" | "SECURITY_SCAN" | "CODE_SCAN" | "SCORING" | null;
  started_at?: string | null;
  finished_at?: string | null;
  error?: { code: string; message: string } | null;
}

export const CATEGORY_LABELS: Record<CategoryKey, string> = {
  documentation: "Documentation",
  ci_cd: "CI/CD",
  security: "Security",
  activity: "Activity",
  issues: "Issues",
  code_health: "Code health",
};
