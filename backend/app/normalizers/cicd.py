"""raw SourceCraft API (cicd/runs) -> CiCdFacts."""

from datetime import datetime
from typing import Any

from ..scoring.facts import CiCdFacts, CiRunFact
from .common import days_between, parse_dt, run_url


def normalize_cicd(runs: list[dict[str, Any]] | None, now: datetime, web_url: str,
                   has_ci_config: bool | None, ci_config_path: str | None,
                   no_data_reason: str | None = None) -> CiCdFacts:
    """runs=None - cicd/runs недоступен (нет прав/ошибка). Поля Run: status, event_type,
    dates.started_at / dates.finished_at (swagger definitions.Run)."""
    if runs is None:
        return CiCdFacts(has_ever_run=False, runs_available=False, no_data_reason=no_data_reason,
                         has_ci_config=has_ci_config, ci_config_path=ci_config_path)

    facts_runs = []
    for run in runs:
        dates = run.get("dates") or {}
        started, finished = parse_dt(dates.get("started_at")), parse_dt(dates.get("finished_at"))
        duration = (finished - started).total_seconds() / 60 if started and finished and finished >= started else None
        slug = str(run.get("slug") or run.get("id") or "")
        facts_runs.append(CiRunFact(
            status=str(run.get("status") or "").lower(),
            finished_at_days_ago=days_between(finished, now),
            duration_minutes=duration,
            event_type=run.get("event_type"),
            ref=slug,
            url=run_url(web_url, slug) if slug else None,
        ))
    # На случай, если API отдаёт не по убыванию времени - упорядочиваем сами (новые первыми).
    facts_runs.sort(key=lambda r: r.finished_at_days_ago if r.finished_at_days_ago is not None else -1)
    return CiCdFacts(has_ever_run=bool(facts_runs), recent_runs=facts_runs, runs_available=True,
                     has_ci_config=has_ci_config, ci_config_path=ci_config_path)
