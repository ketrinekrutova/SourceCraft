"""Соответствует backend/openapi.yaml: Metric, Metrics, Evidence, Recommendation, RepositoryDetail.
Ключ категории CI в ответе API - ci_cd (как в openapi.yaml), во внутреннем домене - cicd."""

from datetime import datetime

from pydantic import BaseModel

from .enums import AnalysisStatus, EvidenceType, MetricStatus, Priority


class Evidence(BaseModel):
    type: EvidenceType
    ref: str
    url: str | None = None


class Component(BaseModel):
    label: str
    points: float | None
    max_points: float
    value: str


class Metric(BaseModel):
    score: int | None
    status: MetricStatus
    summary: str | None = None
    weight: float  # фактический вес после перенормировки при NO_DATA
    base_weight: float  # исходный вес методики
    contribution: float  # вклад в итоговый Score (score × weight)
    components: list[Component] = []
    details: dict = {}
    evidence: list[Evidence] = []


class Metrics(BaseModel):
    documentation: Metric
    ci_cd: Metric
    security: Metric
    activity: Metric
    issues: Metric
    code_health: Metric


class Recommendation(BaseModel):
    id: str
    priority: Priority
    category: str
    title: str
    description: str
    problem: str
    why_it_matters: str
    action: str
    facts: str
    impact: str | None = None
    score_gain: float = 0
    evidence: list[Evidence] = []


class JobInfo(BaseModel):
    job_id: str
    status: AnalysisStatus
    stage: str | None = None
    progress: float = 0
    created_at: datetime | None = None
    finished_at: datetime | None = None
    error: dict | None = None


class PreviousAnalysis(BaseModel):
    health_score: int | None
    analyzed_at: datetime


class RepositoryDetail(BaseModel):
    id: str
    name: str
    full_name: str
    url: str
    description: str | None = None
    language: str | None
    likes: int
    visibility: str
    scope: str  # public | personal
    health_score: int | None
    verdict: str
    status: AnalysisStatus  # статус последнего завершённого анализа или PENDING, если его ещё нет
    last_analyzed_at: datetime | None
    methodology_version: str | None = None
    coverage: float = 0
    metrics: Metrics | None
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[Recommendation] = []
    sources: dict[str, str] = {}
    previous: PreviousAnalysis | None = None
    latest_job: JobInfo | None = None  # последняя задача (в т.ч. упавшая - «анализ не обновлён»)


class HistoryPoint(BaseModel):
    analyzed_at: datetime
    health_score: int | None
    status: AnalysisStatus


class AnalyzeRequest(BaseModel):
    repository_url: str
    scope: str = "public"  # public | personal


class JobAccepted(BaseModel):
    job_id: str
    repository_id: str
    status: AnalysisStatus
    queued_at: datetime | None = None
    status_url: str
    scope: str = "public"


class Job(BaseModel):
    job_id: str
    repository_id: str
    status: AnalysisStatus
    progress: float = 0
    stage: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: dict | None = None
    scope: str = "public"
