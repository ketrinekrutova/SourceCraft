from .result import CATEGORY_WEIGHTS, CategoryScore


def effective_weights(categories: dict[str, CategoryScore]) -> dict[str, float]:
    """Фактические веса: категории без данных получают 0, веса остальных нормируются к сумме 1."""
    available = {name: CATEGORY_WEIGHTS[name] for name, cs in categories.items()
                 if cs.status == "ok" and cs.score is not None}
    total = sum(available.values())
    return {name: (available.get(name, 0) / total if total else 0.0) for name in categories}


def aggregate(categories: dict[str, CategoryScore]) -> int | None:
    """
    Repo Health Score = Σ(score_k × w_k) / Σ w_k  по категориям со status="ok".

    Категории со status="no_data" исключаются из суммы, веса остальных перенормируются, а не
    подставляется 0 - отсутствие данных не ухудшает оценку (ТЗ 3.2, ограничение 11.5).
    Если данных нет ни по одной категории - None («Нет данных» для всего репозитория).
    """
    weights = effective_weights(categories)
    if not any(weights.values()):
        return None
    return round(sum(cs.score * weights[name] for name, cs in categories.items() if weights[name]))


def coverage(categories: dict[str, CategoryScore]) -> float:
    """Доля исходного веса (0..1), по которой есть данные - насколько полно посчитан Score."""
    got = sum(CATEGORY_WEIGHTS[n] for n, cs in categories.items() if cs.status == "ok")
    return got / sum(CATEGORY_WEIGHTS.values())


def verdict(score: int | None) -> str:
    """
    Короткая текстовая интерпретация итогового Score для страницы анализа:
      >= 80        -> "Отличное состояние"
      60-79        -> "Хорошее состояние, есть точки роста"
      40-59        -> "Требует внимания"
      < 40         -> "Критическое состояние"
    """
    if score is None:
        return "Недостаточно данных для оценки"
    if score >= 80:
        return "Отличное состояние"
    if score >= 60:
        return "Хорошее состояние, есть точки роста"
    if score >= 40:
        return "Требует внимания"
    return "Критическое состояние"
