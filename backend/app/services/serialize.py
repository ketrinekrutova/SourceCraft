"""RepoHealthResult -> JSON для хранения в analyses.result_json.

Храним ровно то, что показывается пользователю: страница и выгружаемый отчёт строятся из этой
записи, поэтому отчёт воспроизводим и не требует повторного обращения к источникам."""

from dataclasses import asdict
from typing import Any

from ..scoring.aggregate import verdict
from ..scoring.result import CATEGORY_WEIGHTS, METHODOLOGY_VERSION, RepoHealthResult


def result_to_dict(result: RepoHealthResult, scope: str, sources: dict[str, str]) -> dict[str, Any]:
    categories = {}
    for name, cs in result.categories.items():
        weight = result.weights.get(name, 0.0)
        categories[name] = {
            "score": cs.score,
            "status": cs.status,
            "explanation": cs.explanation,
            "base_weight": CATEGORY_WEIGHTS[name] / 100,
            "weight": round(weight, 4),
            "contribution": round((cs.score or 0) * weight, 2),
            "components": [asdict(c) for c in cs.components],
            "details": cs.details,
            "evidence": [asdict(e) for e in cs.evidence],
        }
    return {
        "methodology_version": METHODOLOGY_VERSION,
        "scope": scope,
        "health_score": result.score,
        "verdict": verdict(result.score),
        "coverage": round(result.coverage, 3),
        "categories": categories,
        "strengths": result.strengths,
        "weaknesses": result.weaknesses,
        "recommendations": [asdict(r) for r in result.recommendations],
        "sources": sources,
    }
