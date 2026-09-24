from ..facts import SecurityFacts
from ..result import CategoryScore


def score_security(facts: SecurityFacts) -> CategoryScore:
      penalty = 20*facts.open_critical_count + 10*facts.open_high_count + 4*facts.open_medium_count + 1*facts.open_low_count
      score   = max(0, 100 - penalty)
      if facts.has_ever_scanned == False:
        return CategoryScore(score=None, status='no_data')
      else:
        return CategoryScore(score=score, status='ok')
