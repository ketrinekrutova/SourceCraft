"""
Result — что возвращает каждая категория и итоговая агрегация.

Это второй общий контракт (после Facts): его должен знать слой API/БД (Фаза 0),
но не должен знать слой сбора данных (Фаза 1).
"""

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["ok", "no_data"]
Priority = Literal["high", "medium", "low"]

CATEGORY_WEIGHTS: dict[str, int] = {
    "security": 20,
    "activity": 15,
    "documentation": 15,
    "cicd": 15,
    "issues": 15,
    "code_health": 20,
}


@dataclass
class CategoryScore:
    score: int | None  # 0..100, либо None при status == "no_data"
    status: Status
    explanation: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class Recommendation:
    category: str
    problem: str
    why_it_matters: str
    action: str
    priority: Priority
    expected_impact: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class RepoHealthResult:
    score: int
    categories: dict[str, CategoryScore]
    recommendations: list[Recommendation]
