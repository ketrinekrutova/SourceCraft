"""
Result - что возвращает каждая категория и итоговая агрегация.

Второй общий контракт (после Facts): его знает слой API/БД, но не знает слой сбора данных.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

METHODOLOGY_VERSION = "1.0"

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

CATEGORY_LABELS: dict[str, str] = {
    "security": "Security",
    "activity": "Activity",
    "documentation": "Documentation",
    "cicd": "CI/CD",
    "issues": "Issues",
    "code_health": "Code health",
}

EvidenceType = Literal["file", "pipeline", "vulnerability", "commit", "issue", "merge_request"]


@dataclass
class Evidence:
    """Тип известен в момент создания (кто вызывает - тот и знает, что это issue или vulnerability),
    поэтому хранится сразу структурой, а не строкой "issue-42"."""

    type: EvidenceType
    ref: str
    url: str | None = None


@dataclass
class Component:
    """Одно слагаемое формулы категории - для блока «объяснение расчёта»."""

    label: str
    points: float | None  # None - показатель не измерен, исключён с перенормировкой внутри категории
    max_points: float
    value: str  # исходное значение метрики человеческим языком


@dataclass
class CategoryScore:
    score: int | None  # 0..100, либо None при status == "no_data"
    status: Status
    explanation: str
    evidence: list[Evidence] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recommendation:
    category: str
    problem: str
    why_it_matters: str
    action: str
    priority: Priority
    expected_impact: str
    evidence: list[Evidence] = field(default_factory=list)
    facts: str = ""  # на каких фактах основан вывод
    category_gain: int = 0
    score_gain: float = 0.0


@dataclass
class RepoHealthResult:
    score: int | None
    categories: dict[str, CategoryScore]
    recommendations: list[Recommendation]
    weights: dict[str, float] = field(default_factory=dict)  # фактические веса после перенормировки
    coverage: float = 0.0  # доля исходного веса, по которой есть данные
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
