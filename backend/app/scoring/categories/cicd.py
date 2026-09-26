from statistics import median

from .._utils import clamp, combine, fmt_days, no_data, ok
from ..facts import CiCdFacts, CiRunFact
from ..result import CategoryScore, Component, Evidence

SUCCESS = {"success"}
FAILURE = {"failed", "timeout"}
# canceled / skipped / rejected / awaiting_approval и незавершённые (created, prepared, processing)
# в знаменатель не берём: это не результат сборки.

RECENT_WINDOW = 10


def _rate(runs: list[CiRunFact]) -> float | None:
    return sum(r.status in SUCCESS for r in runs) / len(runs) if runs else None


def score_cicd(facts: CiCdFacts) -> CategoryScore:
    """
    success   = 60 × success_rate(последние ≤50 завершённых прогонов)
    trend     = 20 × (1 − max(0, rate(прогоны 11..50) − rate(последние 10)))   # штраф за деградацию
    freshness = 20 × clamp(1 − days_since_last_run / 90)
    score     = (success + trend + freshness), перенормировка, если слагаемое не измерить

    Прогонов нет вовсе → score = 0 («CI не используется»), а не «Нет данных»: CI - решение автора.
    Прогоны недоступны (нет прав, ответ организаторов 22.09 п. 2):
      * в дереве нет .sourcecraft/ci.yaml → CI фактически не настроен → 0;
      * конфиг есть → «Нет данных» (статусы прогонов видит только участник репозитория).
    """
    if not facts.runs_available:
        if facts.has_ci_config is False:
            return ok(0, "CI не настроен: в репозитории нет .sourcecraft/ci.yaml",
                      [Component("Наличие CI-конфигурации", 0, 100, "нет")], details={"has_ci_config": False})
        return no_data(
            facts.no_data_reason or "CI-конфигурация найдена, но статусы прогонов недоступны с текущими правами",
            {"has_ci_config": facts.has_ci_config, "ci_config_path": facts.ci_config_path},
        )

    if not facts.has_ever_run or not facts.recent_runs:
        reason = ("CI-конфигурация есть, но прогонов не было" if facts.has_ci_config
                  else "CI не используется: прогонов нет")
        return ok(0, reason, [Component("Прогоны CI", 0, 100, "0")],
                  details={"has_ci_config": facts.has_ci_config, "runs_total": 0})

    completed = [r for r in facts.recent_runs if r.status in SUCCESS | FAILURE]
    success_rate = _rate(completed)
    recent, older = completed[:RECENT_WINDOW], completed[RECENT_WINDOW:]
    recent_rate, older_rate = _rate(recent), _rate(older)
    finished = [r.finished_at_days_ago for r in facts.recent_runs if r.finished_at_days_ago is not None]
    last_run_days = min(finished) if finished else None

    trend_points = None
    if recent_rate is not None and older_rate is not None and len(recent) >= 5 and len(older) >= 5:
        trend_points = 20 * (1 - max(0.0, older_rate - recent_rate))

    components = [
        Component("Доля успешных прогонов", None if success_rate is None else 60 * success_rate, 60,
                  "-" if success_rate is None else f"{round(success_rate * 100)}% из {len(completed)}"),
        Component("Стабильность в динамике", trend_points, 20,
                  "мало прогонов для сравнения" if trend_points is None
                  else f"последние 10: {round(recent_rate * 100)}%, ранее: {round(older_rate * 100)}%"),
        Component("Свежесть последнего прогона", None if last_run_days is None else 20 * clamp(1 - last_run_days / 90), 20,
                  fmt_days(last_run_days) + " назад" if last_run_days is not None else "-"),
    ]
    if all(c.points is None for c in components):
        return no_data("Нет ни одного завершённого прогона CI", {"runs_total": len(facts.recent_runs)})

    score = combine(components)
    fail_rate = 1 - success_rate if success_rate is not None else None
    if fail_rate is None:
        explanation = "Завершённых прогонов пока нет"
    elif fail_rate == 0:
        explanation = f"Все {len(completed)} последних прогонов успешны"
    else:
        explanation = f"{round(fail_rate * 100)}% последних прогонов завершились неуспешно"
    if trend_points is not None and older_rate - recent_rate >= 0.2:
        explanation += "; стабильность ухудшается"

    durations = [r.duration_minutes for r in completed if r.duration_minutes is not None]
    pushes = [r for r in completed if r.event_type == "push"]
    prs = [r for r in completed if r.event_type == "pr_update"]
    failed = [r for r in completed if r.status in FAILURE]
    details = {
        "runs_total": len(facts.recent_runs),
        "completed": len(completed),
        "success_rate": None if success_rate is None else round(success_rate, 3),
        "median_duration_minutes": round(median(durations), 1) if durations else None,
        "push_fail_rate": None if not pushes else round(1 - _rate(pushes), 3),
        "pr_fail_rate": None if not prs else round(1 - _rate(prs), 3),
        "last_run_days_ago": None if last_run_days is None else round(last_run_days, 1),
        "has_ci_config": facts.has_ci_config,
    }
    evidence = [Evidence("pipeline", f"Прогон #{r.ref}: {r.status}", r.url) for r in failed[:5]]
    return ok(score, explanation, components, evidence, details)
