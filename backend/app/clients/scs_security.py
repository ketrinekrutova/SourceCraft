"""Клиент SourceCraft Security API (AppSec). Base URL и схема подтверждены живой спецификацией
https://appsec.sourcecraft.tech/openapi (ссылка на swagger-ui - от организаторов, 16.09).

Особенность спецификации: в DefectGroupDto поля status/severity - числа без таблицы соответствия
(так и сказано в документации SCS). Поэтому количество находок по критичности берём не разбором
списка, а из totalSize запросов с фильтрами по строковым enum (severity=CRITICAL&status=OPEN...),
которые описаны однозначно.

Доступ к AppSec есть только у пользователя с правами на репозиторий (его PAT); отдельного доступа
к AppSec чужих публичных репозиториев не будет (ответ организаторов 22.09, п. 1)."""

from typing import Any

from ..config import settings
from .http import JSONClient, limiter_for

OPEN_STATUSES = ("OPEN", "TRIAGE_IN_PROGRESS", "TRIAGED_TP", "FIX_IN_PROGRESS")
FIXED_STATUSES = ("RESOLVED_FIXED", "RESOLVED_AUTOFIXED")
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
ENGINE_TYPES = ("SAST", "SCA", "SECRETS")


class SCSSecurityClient(JSONClient):
    def __init__(self, token: str):
        super().__init__(
            settings.appsec_api_base_url,
            token,
            limiter_for("appsec_api", settings.appsec_api_rps),
            settings.http_timeout_s,
        )

    async def latest_finished_scan(self, git_repo: str) -> dict[str, Any] | None:
        """Последний успешно завершённый скан. По словам экспертов (19.09) FINISHED гарантирует,
        что все включённые анализаторы отработали; при ошибке любого - FAILED."""
        data = await self.get_json(
            "/v1/scans", {"gitRepo": git_repo, "status": "FINISHED", "pageSize": 20, "pageToken": ""}
        )
        scans = data.get("data") or []
        if not scans:
            return None
        latest = [s for s in scans if s.get("isLatest")]
        return latest[0] if latest else max(scans, key=lambda s: s.get("timeFinished") or 0)

    async def count_defect_groups(self, git_repo: str, scan_uuid: str, *, severity: list[str] | None = None,
                                  status: tuple[str, ...] = OPEN_STATUSES, engine_type: str = "",
                                  page_size: int = 1) -> tuple[int, list[dict[str, Any]]]:
        params: list[tuple[str, Any]] = [
            ("gitRepo", git_repo), ("scanUuid", scan_uuid), ("scanType", ""), ("type", engine_type),
            ("rule", ""), ("file", ""), ("description", ""), ("pageSize", page_size), ("pageToken", ""),
        ]
        params += [("severity", s) for s in severity or []]
        params += [("status", s) for s in status]
        data = await self.get_json("/v1/defect-groups", params)
        return int(data.get("totalSize") or 0), data.get("data") or []
