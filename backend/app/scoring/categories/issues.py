from .._utils import clamp, combine, fmt_days, no_data, ok, plural
from ..facts import IssuesFacts
from ..result import CategoryScore, Component

STALE_DAYS = 30


def score_issues(facts: IssuesFacts) -> CategoryScore:
    """
    backlog          = 40 × (1 − stale_open / open)          # stale = открыт и не обновлялся > 30 дней
    response         = 25 × clamp(1 − avg_first_response_days / 14)
    resolution       = 15 × clamp(1 − median_close_days / 30)
    priority_penalty = 20 × (1 − clamp(critical_or_blocker_open / open / 0.3))
    score = сумма; response/resolution без данных (нет комментариев / закрытых задач) исключаются
    с перенормировкой.

    Issues недоступны с текущими правами → «Нет данных» (ответ организаторов 22.09 п. 4).
    Ни одной задачи за всю историю → тоже «Нет данных»: команда может вести задачи вне трекера
    SourceCraft, по данным одного источника это неотличимо от «задач нет».
    """
    if not facts.issues_available:
        return no_data(facts.no_data_reason or "Issues недоступны с текущими правами доступа")
    if not facts.has_ever_had_issues:
        return no_data("В трекере SourceCraft нет ни одной задачи - задачи могут вестись вне платформы")

    open_n = facts.open_issues_count
    stale_ratio = facts.stale_open_issues_count / open_n if open_n else 0.0
    critical_ratio = facts.critical_or_blocker_open_count / open_n if open_n else 0.0

    components = [
        Component("Доля зависших открытых задач", 40 * (1 - stale_ratio), 40,
                  f"{facts.stale_open_issues_count} из {open_n}"),
        Component("Время до первого ответа",
                  None if facts.avg_first_response_days is None else 25 * clamp(1 - facts.avg_first_response_days / 14), 25,
                  "нет данных" if facts.avg_first_response_days is None else fmt_days(facts.avg_first_response_days)),
        Component("Время до закрытия (медиана)",
                  None if facts.median_close_days is None else 15 * clamp(1 - facts.median_close_days / 30), 15,
                  "нет закрытых задач" if facts.median_close_days is None else fmt_days(facts.median_close_days)),
        Component("Открытые critical/blocker", 20 * (1 - clamp(critical_ratio / 0.3)), 20,
                  str(facts.critical_or_blocker_open_count)),
    ]
    score = combine(components)

    if facts.critical_or_blocker_open_count:
        n = facts.critical_or_blocker_open_count
        explanation = f"{n} {plural(n, 'открытая задача', 'открытые задачи', 'открытых задач')} с приоритетом critical/blocker"
    elif facts.stale_open_issues_count:
        n = facts.stale_open_issues_count
        explanation = f"{n} {plural(n, 'открытая задача не обновлялась', 'открытые задачи не обновлялись', 'открытых задач не обновлялись')} более {STALE_DAYS} дней"
    elif open_n == 0:
        explanation = "Открытых задач нет"
    else:
        explanation = "Задачи обрабатываются своевременно"

    details = {
        "open": open_n,
        "closed": facts.closed_issues_count,
        "stale_open": facts.stale_open_issues_count,
        "critical_or_blocker_open": facts.critical_or_blocker_open_count,
        "avg_first_response_days": None if facts.avg_first_response_days is None else round(facts.avg_first_response_days, 1),
        "median_close_days": None if facts.median_close_days is None else round(facts.median_close_days, 1),
        "created_last90d": facts.created_last90d,
        "closed_last90d": facts.closed_last90d,
        "sample_limited": facts.sample_limited,
    }
    return ok(score, explanation, components, facts.critical_evidence + facts.stale_evidence, details)
