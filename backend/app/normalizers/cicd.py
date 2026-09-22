"""raw SourceCraft API JSON (cicd/runs) -> CiCdFacts."""

from typing import Any

from ..scoring.facts import CiCdFacts


def normalize_cicd(runs_response: dict[str, Any]) -> CiCdFacts:
    """
    runs_response — ответ GET /repos/{org}/{repo}/cicd/runs (пагинировать по next_page_token,
    собрать последние 50). Поля Run: status, dates.finished_at (см. swagger definitions.Run).
    """
    raise NotImplementedError
