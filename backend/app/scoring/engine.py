"""Движок: Facts всех категорий → Repo Health Score, объяснение, сильные/слабые стороны и
рекомендации с рассчитанным эффектом. Чистая функция без I/O - воспроизводима на тех же фактах."""

from .aggregate import aggregate, coverage, effective_weights
from .categories.activity import score_activity
from .categories.cicd import score_cicd
from .categories.code_health import score_code_health
from .categories.documentation import score_documentation
from .categories.issues import score_issues
from .categories.security import score_security
from .recommendations import AllFacts, collect_rules
from .result import CATEGORY_LABELS, CategoryScore, Recommendation, RepoHealthResult

SCORERS = {
    "security": score_security,
    "cicd": score_cicd,
    "documentation": score_documentation,
    "activity": score_activity,
    "issues": score_issues,
    "code_health": score_code_health,
}

STRENGTH_THRESHOLD = 80
WEAKNESS_THRESHOLD = 60
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def score_all(facts: AllFacts) -> dict[str, CategoryScore]:
    return {name: fn(getattr(facts, name)) for name, fn in SCORERS.items()}


def evaluate(facts: AllFacts) -> RepoHealthResult:
    categories = score_all(facts)
    total = aggregate(categories)

    recommendations: list[Recommendation] = []
    for rule in collect_rules(facts):
        before = categories[rule.category]
        after = SCORERS[rule.category](rule.fixed)
        category_gain = max(0, (after.score or 0) - (before.score or 0)) if before.status == "ok" else 0
        patched = {**categories, rule.category: after}
        new_total = aggregate(patched)
        score_gain = max(0.0, (new_total or 0) - (total or 0)) if total is not None else 0.0
        label = CATEGORY_LABELS[rule.category]
        if category_gain:
            impact = f"+{category_gain} к {label}"
            impact += f", ≈ +{score_gain:.0f} к Repo Health Score" if score_gain >= 0.5 else ", < 1 к итоговому Score"
        elif before.status == "no_data":
            impact = f"Категория {label} начнёт учитываться в Score"
        else:
            impact = f"Улучшит показатели категории {label}"
        recommendations.append(Recommendation(
            category=rule.category, problem=rule.problem, why_it_matters=rule.why, action=rule.action,
            priority=rule.priority, expected_impact=impact, evidence=rule.evidence, facts=rule.facts,
            category_gain=category_gain, score_gain=round(score_gain, 1),
        ))
    recommendations.sort(key=lambda r: (PRIORITY_ORDER[r.priority], -r.score_gain, -r.category_gain))

    strengths = [f"{CATEGORY_LABELS[n]}: {cs.explanation}" for n, cs in categories.items()
                 if cs.status == "ok" and cs.score is not None and cs.score >= STRENGTH_THRESHOLD]
    weaknesses = [f"{CATEGORY_LABELS[n]}: {cs.explanation}" for n, cs in categories.items()
                  if cs.status == "ok" and cs.score is not None and cs.score < WEAKNESS_THRESHOLD]

    return RepoHealthResult(
        score=total,
        categories=categories,
        recommendations=recommendations,
        weights=effective_weights(categories),
        coverage=coverage(categories),
        strengths=strengths,
        weaknesses=weaknesses,
    )
