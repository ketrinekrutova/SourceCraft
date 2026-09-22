from .result import CATEGORY_WEIGHTS, CategoryScore


def aggregate(categories: dict[str, CategoryScore]) -> int | None:
     available = []

    for name, category in categories.items():
        if category.status == "ok" and category.score is not None:
            available.append((name, category))

    if not available:
        return 'Невозможно дать оценку репозиторию'

    weighted_sum = 0
    total_weight = 0

    for name, category in available:
        weight = CATEGORY_WEIGHTS[name]

        weighted_sum += category.score * weight
        total_weight += weight

    score = weighted_sum / total_weight

    return round(score)
    """
    README 3.1: категории со status="no_data" исключаются из суммы, веса остальных
    перенормируются (CATEGORY_WEIGHTS из result.py), а не подставляется 0.

    "Все 6 категорий no_data одновременно" физически недостижимо при обычной работе (по нашим
    правилам no_data бывает только у Security/Issues/Activity/Code health, а Documentation
    no_data — только при is_empty_repo, что обрабатывается ДО вызова этой функции, отдельным
    сценарием CHECK.md №5). Тем не менее для защиты от деления на ноль: если available пуст,
    вернуть None, а не падать — вызывающий код должен считать это тем же самым "нет данных"
    для всего репозитория.
    """
    raise NotImplementedError


def verdict(score: int) -> str:
    """
    Короткая текстовая интерпретация итогового Score для страницы анализа (README 3.4).
    Пороги подтверждены (граница 60-79 подобрана так, чтобы пример из макета, Score=74,
    попадал в "Хорошее состояние, есть точки роста"):
      >= 80        -> "Отличное состояние"
      60-79        -> "Хорошее состояние, есть точки роста"
      40-59        -> "Требует внимания"
      < 40         -> "Критическое состояние"
    """
    if score >= 80:
        return "Отличное состояние"
    if score >= 60:
        return "Хорошее состояние, есть точки роста"
    if score >= 40:
        return "Требует внимания"
    return "Критическое состояние"
