from .._utils import clamp, no_data, ok
from ..facts import CodeHealthFacts
from ..result import CategoryScore, Component

STALE_MARKER_DAYS = 180


def score_code_health(facts: CodeHealthFacts) -> CategoryScore:
    """
    density   = 60 × (1 − clamp(markers_per_kloc / 10))     # TODO/FIXME/HACK/XXX на 1000 строк кода
    freshness = 40 × (1 − stale_markers / markers)           # stale = старше 180 дней по git blame
    score = density + freshness;  0 маркеров → freshness = 40

    Нормировка на KLOC - чтобы большой репозиторий не наказывался сильнее маленького.
    «Нет данных» - только сбой клонирования или отсутствие исходного кода (например, репозиторий
    с одной документацией).
    """
    if not facts.clone_succeeded:
        return no_data(facts.no_data_reason or "Не удалось получить содержимое репозитория")
    if facts.kloc <= 0:
        return no_data("Исходного кода для анализа не найдено")

    per_kloc = facts.markers_count / facts.kloc
    stale_ratio = facts.stale_markers_count / facts.markers_count if facts.markers_count else 0.0
    density = 60 * (1 - clamp(per_kloc / 10))
    freshness = 40 * (1 - stale_ratio)
    components = [
        Component("Плотность TODO/FIXME", density, 60, f"{per_kloc:.1f} на 1000 строк"),
        Component("Давность маркеров", freshness, 40,
                  f"{facts.stale_markers_count} из {facts.markers_count} старше {STALE_MARKER_DAYS} дней"),
    ]

    if facts.markers_count == 0:
        explanation = "Маркеров TODO/FIXME в коде нет"
    else:
        explanation = f"Найдено {facts.markers_count} TODO/FIXME"
        if facts.stale_markers_count:
            explanation += f", {facts.stale_markers_count} из них старше шести месяцев"
    if facts.sampled:
        explanation += " (по выборке файлов крупного репозитория)"

    details = {
        "markers": facts.markers_count,
        "markers_by_type": facts.markers_by_type,
        "stale_markers": facts.stale_markers_count,
        "kloc": round(facts.kloc, 1),
        "markers_per_kloc": round(per_kloc, 2),
        "source_files": facts.source_files,
        "large_files": facts.large_files,
        "sampled": facts.sampled,
        "age_method": facts.age_method,
    }
    return ok(density + freshness, explanation, components, facts.evidence, details)
