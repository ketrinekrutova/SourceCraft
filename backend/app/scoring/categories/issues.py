from ..facts import IssuesFacts
from ..result import CategoryScore
from _utils import clamp

def score_issues(facts: IssuesFacts) -> CategoryScore:
      backlog          = 40 * (1 - facts.stale_open_issues_count)   # stale = открыт и не обновлялся >30 дней
      response         = 25 * clamp(1 - facts.avg_first_response_days/14, 0, 1)
      resolution       = 15 * clamp(1 - facts.median_close_days/30, 0, 1)
      priority_penalty = 20 * (1 - clamp(facts.critical_or_blocker_open_count / 0.3, 0, 1))
      score = backlog + response + resolution + priority_penalty
      if facts.has_ever_had_issues == False:
        return CategoryScore(score=None, status='no_data')
      else:
          return CategoryScore(score=score, status= 'ok')
