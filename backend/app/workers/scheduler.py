"""
Планировщик (APScheduler, простой вариант для MVP — см. README раздел 2). Периодичность —
наше решение, зафиксировать и обосновать при реализации (README 4.4).
"""


def setup_scheduler() -> None:
    """
    Пример состава задач (реализовать вместе с workers/fast_pass.py и full_pass.py):
      - fast_pass.run_fast_pass_for_all_public_repos, раз в 24 часа
      - full_pass.run_full_pass_for_top_n, раз в 24 часа
    """
    raise NotImplementedError
