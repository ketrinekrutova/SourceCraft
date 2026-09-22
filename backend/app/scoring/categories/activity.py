from ..facts import ActivityFacts
from ..result import CategoryScore


def score_activity(facts: ActivityFacts) -> CategoryScore:
    """
    README 3.2, Активность проекта (15%):
      recency      = 35 * clamp(1 - days_since_last_commit/180, 0, 1)
      frequency    = 25 * clamp(commits_per_week_last90d / 5, 0, 1)
      contributors = 15 * clamp(active_authors_last90d / 3, 0, 1)
      pr_activity  = 20 * clamp(merged_prs_last90d / 10, 0, 1)
      release      = 5 (<90 дней) | 2 (<180 дней) | 0
      score = recency + frequency + contributors + pr_activity + release

    Непустой репозиторий всегда имеет данные (не может быть no_data, кроме сбоя CLI).
    """
    raise NotImplementedError
