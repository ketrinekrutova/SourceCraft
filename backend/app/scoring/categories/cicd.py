from ..facts import CiCdFacts
from ..result import CategoryScore
from _utils import clamp

def score_cicd(facts: CiCdFacts) -> CategoryScore:
      
      success   = sum('success' in x for x in facts.recent_runs)/50
      trend     = 20 * (1 - max(0, sum('success' in x for x in facts.recent_runs[:10:-1]) - sum('success' in x for x in facts.recent_runs[:10])))  # штраф за деградацию
      freshness = 20 * clamp(1 - facts.recent_runs[0][1]/90, 0, 1)
      score = success*60 + trend + freshness
      if facts.has_ever_run == False:
            return CategoryScore(score= 0, status='ok')
      return CategoryScore(score=score, status='ok')
    #has_ever_run == False -> score=0, status="ok" (осознанно не no_data, README 3.1).
    
    
