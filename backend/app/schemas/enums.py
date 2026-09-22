"""Строковые enum'ы ответа API — значения и написание (ВЕРХНИЙ_РЕГИСТР) взяты из backend/openapi.yaml,
а не придуманы заново. Внутренний домен (scoring/facts.py, scoring/result.py) использует свои,
питонические обозначения (нижний регистр) — соответствие между ними проводит роутер при сборке ответа."""

from typing import Literal

AnalysisStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED", "PARTIAL", "FAILED"]
MetricStatus = Literal["OK", "NO_DATA"]
Priority = Literal["HIGH", "MEDIUM", "LOW"]
EvidenceType = Literal["file", "pipeline", "vulnerability", "commit", "issue", "merge_request"]
