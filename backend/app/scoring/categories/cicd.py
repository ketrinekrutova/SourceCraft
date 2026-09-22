from ..facts import CiCdFacts
from ..result import CategoryScore


def score_cicd(facts: CiCdFacts) -> CategoryScore:
    """
    README 3.2, CI/CD (15%):
      success   = success_rate(последние 50 ранов)                 -> вклад x60
      trend     = 20 * (1 - max(0, older10_rate - recent10_rate))  # штраф за деградацию
      freshness = 20 * clamp(1 - days_since_last_run/90, 0, 1)
      score = success*60 + trend + freshness

    has_ever_run == False -> score=0, status="ok" (осознанно не no_data, README 3.1).
    """
    raise NotImplementedError
