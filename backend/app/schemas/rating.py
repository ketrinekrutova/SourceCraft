"""Соответствует backend/openapi.yaml: RepositorySummary, RepositoryPage (GET /repositories)."""

from datetime import datetime

from pydantic import BaseModel

from .enums import AnalysisStatus


class RepositorySummary(BaseModel):
    id: str
    name: str
    url: str
    health_score: int | None
    likes: int
    language: str | None
    last_activity_at: datetime | None
    last_analyzed_at: datetime | None
    status: AnalysisStatus


class RepositoryPage(BaseModel):
    items: list[RepositorySummary]
    page: int
    limit: int
    total: int
