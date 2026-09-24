from ..facts import ActivityFacts
from ..result import CategoryScore
from _utils import clamp

def score_activity(facts: ActivityFacts) -> CategoryScore:
      recency      = 35 * clamp(1 - facts.days_since_last_commit/180, 0, 1)
      frequency    = 25 * clamp(facts.commits_per_week_last90d / 5, 0, 1)
      contributors = 15 * clamp(facts.active_authors_last90d / 3, 0, 1)
      pr_activity  = 20 * clamp(facts.merged_prs_last90d / 10, 0, 1)
      if facts.days_since_last_release <90:
            release = 5
      else:
            if facts.days_since_last_release < 180 and facts.days_since_last_release >= 90:
                release = 2
            else:
                  release = 0                  
      score = recency + frequency + contributors + pr_activity + release
    
      return CategoryScore(score= score, status= 'ok')
