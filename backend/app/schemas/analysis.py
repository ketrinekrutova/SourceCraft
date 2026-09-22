"""Соответствует backend/openapi.yaml: Metric, Metrics, Evidence, Recommendation, RepositoryDetail
(GET /repositories/{id}). Ключи Metrics — documentation, ci_cd, security, activity, issues, code_health
(именно ci_cd, не cicd — как в openapi.yaml)."""

from datetime import datetime

from pydantic import BaseModel

from .enums import AnalysisStatus, EvidenceType, MetricStatus, Priority


class Evidence(BaseModel):
    type: EvidenceType
    ref: str
    url: str | None = None


class Metric(BaseModel):
    score: int | None
    status: MetricStatus
    summary: str | None = None
    weight: float  # фактический вес категории после перенормировки при NO_DATA (README 3.1)
    details: dict = {}  # сырые показатели категории для раскрывающегося блока в UI


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
    impact: str | None = None
    evidence: list[Evidence] = []


class RepositoryDetail(BaseModel):
    id: str
    name: str
    url: str
    language: str | None
    health_score: int | None
    verdict: str  # короткий вердикт ("Хорошее состояние, есть точки роста"). Есть и в openapi.yaml.
    status: AnalysisStatus
    last_analyzed_at: datetime | None
    metrics: Metrics
    recommendations: list[Recommendation]
    # missing_data решили не делать (вариант A): "--" в UI для отсутствующих данных рисуется
    # по Metric.status == "NO_DATA" на уровне целой категории — этого достаточно, отдельное
    # поле под по-индикаторную гранулярность не нужно (README 3.1).
    # Вопрос записан в openapi.yaml, ждём уточнения.
