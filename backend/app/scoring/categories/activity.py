from .._utils import clamp, combine, fmt_days, no_data, ok
from ..facts import ActivityFacts
from ..result import CategoryScore, Component


def score_activity(facts: ActivityFacts) -> CategoryScore:
    """
    recency      = 35 × clamp(1 − days_since_last_commit / 180)
    frequency    = 25 × clamp(commits_per_week_last90d / 5)      # только непустые не-merge коммиты
    contributors = 15 × clamp(active_authors_last90d / 3)
    pr_activity  = 20 × clamp(merged_prs_last90d / 10)
    release      = 5 (релиз < 90 дней) | 2 (< 180 дней) | 0
    score = сумма; слагаемое, которое не удалось измерить (API недоступен), исключается с перенормировкой.

    Потолки clamp - защита от накрутки: 100 пустых коммитов в день не дают больше, чем 5 настоящих
    в неделю, а пустые коммиты (без изменений файлов) не считаются вовсе.
    """
    if not facts.history_available or facts.days_since_last_commit is None:
        return no_data(facts.no_data_reason or "Не удалось получить git-историю репозитория")

    if not facts.releases_available:
        release_points = None
    elif facts.days_since_last_release is None:
        release_points = 0
    elif facts.days_since_last_release < 90:
        release_points = 5
    elif facts.days_since_last_release < 180:
        release_points = 2
    else:
        release_points = 0

    components = [
        Component("Давность последнего коммита", 35 * clamp(1 - facts.days_since_last_commit / 180), 35,
                  fmt_days(facts.days_since_last_commit) + " назад"),
        Component("Частота коммитов (90 дней)", 25 * clamp(facts.commits_per_week_last90d / 5), 25,
                  f"{facts.commits_per_week_last90d:.1f} в неделю"),
        Component("Активные авторы (90 дней)", 15 * clamp(facts.active_authors_last90d / 3), 15,
                  str(facts.active_authors_last90d)),
        Component("Принятые merge requests (90 дней)",
                  None if facts.merged_prs_last90d is None else 20 * clamp(facts.merged_prs_last90d / 10), 20,
                  "нет доступа" if facts.merged_prs_last90d is None else str(facts.merged_prs_last90d)),
        Component("Релизы", release_points, 5,
                  "нет доступа" if not facts.releases_available
                  else ("релизов нет" if facts.days_since_last_release is None
                        else fmt_days(facts.days_since_last_release) + " назад")),
    ]
    score = combine(components)

    d = facts.days_since_last_commit
    if d > 365:
        explanation = f"Проект не обновлялся больше года (последний коммит {fmt_days(d)} назад)"
    elif d > 180:
        explanation = f"Последний коммит {fmt_days(d)} назад - проект почти не развивается"
    elif score >= 75:
        explanation = "Проект активно развивается"
    elif facts.commits_last90d == 0:
        explanation = "За последние 90 дней коммитов не было"
    else:
        explanation = (f"{facts.commits_last90d} коммитов за 90 дней, "
                       f"активных авторов: {facts.active_authors_last90d}")

    details = {
        "days_since_last_commit": round(d, 1),
        "commits_last90d": facts.commits_last90d,
        "commits_prev90d": facts.commits_prev90d,
        "empty_commits_excluded": facts.empty_commits_excluded,
        "active_authors_last90d": facts.active_authors_last90d,
        "top_author_share": facts.top_author_share,
        "contributors_total": facts.contributors_total,
        "merged_prs_last90d": facts.merged_prs_last90d,
        "open_prs": facts.open_prs,
        "releases_total": facts.releases_total,
    }
    evidence = [facts.last_commit_evidence] if facts.last_commit_evidence else []
    return ok(score, explanation, components, evidence, details)
