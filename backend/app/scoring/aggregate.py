from .result import CategoryScore


def aggregate(categories: dict[str, CategoryScore]) -> int:
    """
    README 3.1: категории со status="no_data" исключаются из суммы, веса остальных
    перенормируются (CATEGORY_WEIGHTS из result.py), а не подставляется 0.

    Если все 6 категорий no_data — обрабатывается на уровне выше (репозиторий целиком),
    сюда такой вызов приходить не должен.
    """
    raise NotImplementedError


def verdict(score: int) -> str:
    """Короткая текстовая интерпретация итогового Score для страницы анализа (README 3.4)."""
    raise NotImplementedError
