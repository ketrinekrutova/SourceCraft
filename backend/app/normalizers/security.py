"""Ответы AppSec API (скан + счётчики групп дефектов) -> SecurityFacts."""

from datetime import datetime, timezone
from typing import Any

from ..scoring.facts import SecurityFacts
from ..scoring.result import Evidence
from .common import security_url


def defect_evidence(group: dict[str, Any], severity: str, web_url: str) -> Evidence:
    location = group.get("fileName") or ""
    if location and group.get("startLine"):
        location += f":{group['startLine']}"
    ref = f"#{group.get('publicId', '?')} {severity} {group.get('ruleName') or group.get('ruleId') or ''}".strip()
    if location:
        ref += f" - {location}"
    return Evidence("vulnerability", ref, security_url(web_url))


def normalize_security(scan: dict[str, Any] | None, open_by_severity: dict[str, int], open_by_engine: dict[str, int],
                       secrets_by_severity: dict[str, int], fixed_count: int, evidence: list[Evidence],
                       secrets_evidence: list[Evidence], now: datetime, no_data_reason: str | None = None) -> SecurityFacts:
    if scan is None:
        return SecurityFacts(has_ever_scanned=False, no_data_reason=no_data_reason)
    finished_ms = scan.get("timeFinished")
    finished_days = None
    if finished_ms:
        finished_days = max(0.0, (now - datetime.fromtimestamp(finished_ms / 1000, tz=timezone.utc)).total_seconds() / 86400)
    return SecurityFacts(
        has_ever_scanned=True,
        open_critical_count=open_by_severity.get("CRITICAL", 0),
        open_high_count=open_by_severity.get("HIGH", 0),
        open_medium_count=open_by_severity.get("MEDIUM", 0),
        open_low_count=open_by_severity.get("LOW", 0),
        open_by_engine=open_by_engine,
        secrets_by_severity=secrets_by_severity,
        fixed_count=fixed_count,
        scan_finished_days_ago=finished_days,
        evidence=evidence,
        secrets_evidence=secrets_evidence,
    )
