"""raw SCS API JSON -> SecurityFacts. Реализовать на Фазе 1, когда появятся реальные образцы ответов."""

from typing import Any

from ..scoring.facts import SecurityFacts


def normalize_security(scans_latest: dict[str, Any] | None, defect_groups: dict[str, Any] | None) -> SecurityFacts:
    """
    scans_latest — ответ GET /v1/scans/latest?gitRepo=... (None, если сканов не было -> has_ever_scanned=False).
    defect_groups — ответ GET /v1/defect-groups?gitRepo=...&status=<не RESOLVED*> (открытые находки).
    Считать count по полю severity, RESOLVED_FP не учитывать (README 3.2).
    """
    raise NotImplementedError
