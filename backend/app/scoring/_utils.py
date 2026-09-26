from .result import CategoryScore, Component, Evidence


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Ограничивает x диапазоном [lo, hi]. Используется во всех формулах категорий."""
    return max(lo, min(hi, x))


def combine(components: list[Component]) -> int:
    """Сумма баллов измеренных слагаемых, перенормированная на их максимум.

    Слагаемое с points=None (показатель не удалось измерить, например нет ни одной закрытой
    задачи для «времени до закрытия») исключается, а не считается нулём - то же правило
    «нет данных ≠ плохо», что и на уровне категорий, только внутри категории."""
    measured = [c for c in components if c.points is not None]
    total_max = sum(c.max_points for c in measured)
    if total_max <= 0:
        return 0
    return round(100 * sum(c.points for c in measured) / total_max)


def no_data(reason: str, details: dict | None = None) -> CategoryScore:
    return CategoryScore(score=None, status="no_data", explanation=reason, details=details or {})


def ok(score: float, explanation: str, components: list[Component] | None = None,
       evidence: list[Evidence] | None = None, details: dict | None = None) -> CategoryScore:
    return CategoryScore(
        score=int(round(clamp(score, 0, 100))),
        status="ok",
        explanation=explanation,
        components=components or [],
        evidence=evidence or [],
        details=details or {},
    )


def plural(n: int, one: str, few: str, many: str) -> str:
    n_abs = abs(n) % 100
    if 11 <= n_abs <= 19:
        return many
    last = n_abs % 10
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


def fmt_days(days: float | None) -> str:
    if days is None:
        return "-"
    d = int(round(days))
    return f"{d} {plural(d, 'день', 'дня', 'дней')}"
