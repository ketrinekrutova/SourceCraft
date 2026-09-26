"""Выгрузка отчёта в Markdown (ТЗ 3.4). Рендерит ровно тот RepositoryDetail, который отдаёт
GET /repositories/{id}, - отчёт и страница не расходятся."""

from ..schemas.analysis import Metric, RepositoryDetail

CATEGORY_TITLES = {
    "documentation": "Documentation",
    "ci_cd": "CI/CD",
    "security": "Security",
    "activity": "Activity",
    "issues": "Issues",
    "code_health": "Code health",
}
PRIORITY_TITLES = {"HIGH": "Высокий", "MEDIUM": "Средний", "LOW": "Низкий"}
NO_DATA = "Нет данных"


def _score(metric: Metric) -> str:
    return NO_DATA if metric.status == "NO_DATA" else f"{metric.score}/100"


def _md(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _link(ref: str, url: str | None) -> str:
    return f"[{_md(ref)}]({url})" if url else _md(ref)


def render_markdown_report(detail: RepositoryDetail) -> str:
    lines: list[str] = []
    add = lines.append
    score = "Нет данных" if detail.health_score is None else f"{detail.health_score}/100"
    add(f"# {detail.full_name}")
    add("")
    add(f"**Repo Health Score: {score}** - {detail.verdict}")
    add("")
    add(f"- Ссылка: {detail.url}")
    add(f"- Дата анализа: {detail.last_analyzed_at:%Y-%m-%d %H:%M} UTC" if detail.last_analyzed_at else "- Дата анализа: -")
    add(f"- Основной язык: {detail.language or '-'}")
    add(f"- Режим: {'личный анализ по PAT владельца (включая AppSec)' if detail.scope == 'personal' else 'публичный анализ (открытые данные)'}")
    add(f"- Полнота данных: {round(detail.coverage * 100)}% веса методики")
    if detail.methodology_version:
        add(f"- Версия методики: {detail.methodology_version}")
    add("")

    if detail.metrics is None:
        add("Анализ ещё не выполнялся.")
        return "\n".join(lines) + "\n"

    add("## Оценки по категориям")
    add("")
    add("| Категория | Оценка | Вес (исходный → фактический) | Вклад в Score | Пояснение |")
    add("|---|---|---|---|---|")
    metrics = detail.metrics.model_dump()
    for key, title in CATEGORY_TITLES.items():
        m = Metric(**metrics[key])
        weight = f"{round(m.base_weight * 100)}% → {round(m.weight * 100)}%"
        contribution = "-" if m.status == "NO_DATA" else f"{m.contribution:.1f}"
        add(f"| {title} | {_score(m)} | {weight} | {contribution} | {_md(m.summary)} |")
    add("")
    add("Repo Health Score = Σ(оценка категории × вес) по категориям с данными; веса категорий "
        "со статусом «Нет данных» перераспределяются пропорционально между остальными.")
    add("")

    if detail.strengths or detail.weaknesses:
        add("## Сильные и слабые стороны")
        add("")
        for s in detail.strengths:
            add(f"- ✅ {s}")
        for w in detail.weaknesses:
            add(f"- ⚠️ {w}")
        add("")

    add("## Рекомендации")
    add("")
    if not detail.recommendations:
        add("Критичных рекомендаций нет.")
    for i, rec in enumerate(detail.recommendations, start=1):
        add(f"### {i}. [{PRIORITY_TITLES[rec.priority]} приоритет] {rec.title}")
        add("")
        add(f"- **Почему важно:** {rec.why_it_matters}")
        if rec.facts:
            add(f"- **Факты:** {rec.facts}")
        add(f"- **Что сделать:** {rec.action}")
        if rec.impact:
            add(f"- **Ожидаемый эффект:** {rec.impact}")
        if rec.evidence:
            add("- **Подтверждения:** " + "; ".join(_link(e.ref, e.url) for e in rec.evidence[:10]))
        add("")

    add("## Объяснение расчёта")
    add("")
    for key, title in CATEGORY_TITLES.items():
        m = Metric(**metrics[key])
        add(f"### {title}: {_score(m)}")
        add("")
        if m.status == "NO_DATA":
            add(f"{NO_DATA}: {m.summary}. Категория исключена из расчёта и не снижает Score.")
            add("")
            continue
        if m.components:
            add("| Показатель | Значение | Баллы |")
            add("|---|---|---|")
            for c in m.components:
                if c.points is None:
                    points = "не измерено (исключено)"
                elif c.max_points:
                    points = f"{c.points:.1f} из {c.max_points:g}"
                else:
                    points = f"{c.points:.0f}"
                add(f"| {_md(c.label)} | {_md(c.value)} | {points} |")
            add("")
        if m.evidence:
            add("Подтверждающие факты: " + "; ".join(_link(e.ref, e.url) for e in m.evidence[:10]))
            add("")

    add("---")
    add("Сформировано сервисом SourceCraft Repo Health. Отсутствие данных не считается плохим результатом.")
    return "\n".join(lines) + "\n"
