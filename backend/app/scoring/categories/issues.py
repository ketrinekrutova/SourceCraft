from ..facts import IssuesFacts
from ..result import CategoryScore


def score_issues(facts: IssuesFacts) -> CategoryScore:
    """
    README 3.2, Issues (15%):
      backlog          = 40 * (1 - stale_ratio)   # stale = открыт и не обновлялся >30 дней
      response         = 25 * clamp(1 - avg_first_response_days/14, 0, 1)
      resolution       = 15 * clamp(1 - median_close_days/30, 0, 1)
      priority_penalty = 20 * (1 - clamp(critical_or_blocker_open_ratio / 0.3, 0, 1))
      score = backlog + response + resolution + priority_penalty

    has_ever_had_issues == False -> status="no_data" (README 3.1).
    """
    raise NotImplementedError
