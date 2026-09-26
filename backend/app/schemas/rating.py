"""Соответствует backend/openapi.yaml: RepositorySummary, RepositoryPage (GET /repositories)."""

from datetime import datetime

from pydantic import BaseModel

from .enums import AnalysisStatus


class RepositorySummary(BaseModel):
    id: str
    name: str
    full_name: str
    url: str
    health_score: int | None
    likes: int
    language: str | None
    last_activity_at: datetime | None
    last_analyzed_at: datetime | None
    status: AnalysisStatus
    coverage: float | None = None


class CatalogSummary(BaseModel):
    catalog_total: int
    analyzed_total: int
    last_analyzed_at: datetime | None


class RepositoryPage(BaseModel):
    items: list[RepositorySummary]
    page: int
    limit: int
    total: int
    summary: CatalogSummary
