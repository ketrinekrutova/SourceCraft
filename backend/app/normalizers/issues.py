"""raw /issues (+ комментарии выборки задач) -> IssuesFacts."""

from datetime import datetime, timedelta
from statistics import median
from typing import Any

from ..scoring.facts import IssuesFacts
from ..scoring.result import Evidence
from .common import days_between, issue_url, parse_dt

OPEN_TYPES = {"initial", "in_progress", "paused"}
CLOSED_TYPES = {"completed", "cancelled"}
STALE_DAYS = 30


def _status_type(issue: dict[str, Any]) -> str:
    return str(((issue.get("status") or {}).get("status_type")) or "initial").lower()


def normalize_issues(issues: list[dict[str, Any]] | None, comments_by_slug: dict[str, list[dict[str, Any]]],
                     now: datetime, web_url: str, limit_hit: bool = False,
                     no_data_reason: str | None = None) -> IssuesFacts:
    """issues=None - API недоступен. comments_by_slug - комментарии для выборки последних задач
    (дорого по запросам, поэтому только последние N - см. settings.issue_comments_sample).

    Время до первого ответа - первый комментарий НЕ автора задачи."""
    if issues is None:
        return IssuesFacts(has_ever_had_issues=False, issues_available=False, no_data_reason=no_data_reason)
    if not issues:
        return IssuesFacts(has_ever_had_issues=False)

    open_issues = [i for i in issues if _status_type(i) in OPEN_TYPES]
    closed_issues = [i for i in issues if _status_type(i) in CLOSED_TYPES]
    stale_border = now - timedelta(days=STALE_DAYS)
    stale = [i for i in open_issues if (parse_dt(i.get("updated_at")) or parse_dt(i.get("created_at")) or now) < stale_border]
    critical = [i for i in open_issues if str(i.get("priority") or "").lower() in ("critical", "blocker")]

    close_days = []
    for issue in issues:
        if _status_type(issue) == "completed":
            d = days_between(parse_dt(issue.get("created_at")), parse_dt(issue.get("completed_at")) or now)
            if d is not None and parse_dt(issue.get("completed_at")):
                close_days.append(d)

    response_days = []
    for issue in issues:
        comments = comments_by_slug.get(str(issue.get("slug")))
        if comments is None:
            continue
        author = ((issue.get("author") or {}).get("id"))
        created = parse_dt(issue.get("created_at"))
        replies = sorted(
            (parse_dt(c.get("created_at")) for c in comments if ((c.get("author") or {}).get("id")) != author),
            key=lambda d: d or now,
        )
        replies = [r for r in replies if r is not None]
        if created and replies:
            response_days.append(days_between(created, replies[0]) or 0.0)

    window = now - timedelta(days=90)

    def ev(issue: dict[str, Any]) -> Evidence:
        slug = str(issue.get("slug") or issue.get("id"))
        return Evidence("issue", f"#{slug} {str(issue.get('title') or '')[:80]}".strip(), issue_url(web_url, slug))

    return IssuesFacts(
        has_ever_had_issues=True,
        open_issues_count=len(open_issues),
        closed_issues_count=len(closed_issues),
        stale_open_issues_count=len(stale),
        avg_first_response_days=sum(response_days) / len(response_days) if response_days else None,
        median_close_days=median(close_days) if close_days else None,
        critical_or_blocker_open_count=len(critical),
        created_last90d=sum(1 for i in issues if (parse_dt(i.get("created_at")) or now) >= window),
        closed_last90d=sum(1 for i in closed_issues if (parse_dt(i.get("completed_at")) or window) > window),
        sample_limited=limit_hit,
        stale_evidence=[ev(i) for i in sorted(stale, key=lambda i: i.get("updated_at") or "")[:10]],
        critical_evidence=[ev(i) for i in critical[:10]],
    )
