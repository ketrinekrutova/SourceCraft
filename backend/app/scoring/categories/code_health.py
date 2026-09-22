from ..facts import CodeHealthFacts
from ..result import CategoryScore


def score_code_health(facts: CodeHealthFacts) -> CategoryScore:
    """
    README 3.2, Code health (20%):
      density   = 60 * (1 - clamp(markers_per_kloc / 10, 0, 1))
      freshness = 40 * (1 - stale_marker_ratio)   # stale = старше 180 дней; 0 маркеров -> freshness=40
      score = density + freshness

    clone_succeeded == False -> status="no_data" (сбой клонирования/таймаут, не отсутствие TODO).
    """
    raise NotImplementedError
