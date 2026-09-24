from ..facts import CodeHealthFacts
from ..result import CategoryScore
from _utils import clamp

def score_code_health(facts: CodeHealthFacts) -> CategoryScore:
      density   = 60 * (1 - clamp(facts.markers_per_kloc / 10, 0, 1))
      freshness = 40 * (1 - facts.stale_marker_count)   # stale = старше 180 дней; 0 маркеров -> freshness=40
      score = density + freshness
      if facts.clone_succeeded == False:
           return CategoryScore(score=None, status='no_data')
      else:
            return CategoryScore(score=score, status='ok')
