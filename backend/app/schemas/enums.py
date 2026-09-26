"""Строковые enum'ы ответа API - значения и написание (ВЕРХНИЙ_РЕГИСТР) взяты из backend/openapi.yaml.
Внутренний домен (scoring/) использует нижний регистр - соответствие проводит слой API (routers/_views.py)."""

from typing import Literal

AnalysisStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED", "PARTIAL", "FAILED"]
MetricStatus = Literal["OK", "NO_DATA"]
Priority = Literal["HIGH", "MEDIUM", "LOW"]
EvidenceType = Literal["file", "pipeline", "vulnerability", "commit", "issue", "merge_request"]
