"""
Клиент SourceCraft Security API (SCS). Base URL НЕ ПОДТВЕРЖДЁН организаторами — рабочая
гипотеза appsec.sourcecraft.tech из documents/Источники_данных_по_категориям.pdf, проверить
на Этапе 0 (CHECK.md A3). Пути и поля — из documents/SCS_API_1.0.0_draft.pdf.
"""

from typing import Any


class SCSSecurityClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url
        self.token = token

    async def get_latest_scan(self, git_repo: str) -> dict[str, Any]:
        """GET /v1/scans/latest?gitRepo={git_repo} -> ScanSummaryDto.
        git_repo — внутренний id или UUID; соответствие Repository.id из основного API не подтверждено
        (CHECK.md B3), проверить первым же реальным запросом."""
        raise NotImplementedError

    async def list_defect_groups(self, git_repo: str, scan_uuid: str | None = None,
                                  severity: list[str] | None = None,
                                  status: list[str] | None = None,
                                  page_token: str | None = None, page_size: int = 50) -> dict[str, Any]:
        """GET /v1/defect-groups?gitRepo=...&severity=...&status=... (повтор ключа для нескольких значений).
        page_size: 1..250, по умолчанию 50."""
        raise NotImplementedError
