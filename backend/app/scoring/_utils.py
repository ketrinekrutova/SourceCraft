def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Ограничивает x диапазоном [lo, hi]. Используется во всех формулах категорий (README раздел 3.2)."""
    return max(lo, min(hi, x))
