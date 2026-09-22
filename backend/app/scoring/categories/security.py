from ..facts import SecurityFacts
from ..result import CategoryScore


def score_security(facts: SecurityFacts) -> CategoryScore:
    """
    README 3.2, Security (20%):
      penalty = 20*count(CRITICAL) + 10*count(HIGH) + 4*count(MEDIUM) + 1*count(LOW)
      score   = max(0, 100 - penalty)

    has_ever_scanned == False -> status="no_data" (сканов не было, см. README 3.1).
    Учитывать только открытые находки (не RESOLVED*).
    """
    raise NotImplementedError
