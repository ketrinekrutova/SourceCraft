"""git-история (коммиты) + contributors/pulls/releases из API -> ActivityFacts."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from ..clients.git_client import Commit
from ..scoring.facts import ActivityFacts
from ..scoring.result import Evidence
from .common import commit_url, days_between, parse_dt

WINDOW_DAYS = 90


def normalize_activity(commits: list[Commit] | None, head_commit_ts: int | None, now: datetime, web_url: str,
                       pulls: list[dict[str, Any]] | None, releases: list[dict[str, Any]] | None,
                       contributors: list[dict[str, Any]] | None, no_data_reason: str | None = None) -> ActivityFacts:
    """commits - коммиты без merge за 180 дней (окно shallow-клона); None - клон не удался.

    Защита от накрутки: коммиты без изменений файлов («пустые») не считаются в частоте и авторах.
    Время мержа PR в API нет (merged_at отсутствует, эксперты подтвердили) - для PR в статусе
    merged берём updated_at как приближение."""
    if commits is None or head_commit_ts is None:
        return ActivityFacts(history_available=False, no_data_reason=no_data_reason)

    last_commit = datetime.fromtimestamp(head_commit_ts, tz=timezone.utc)
    window_start = (now - timedelta(days=WINDOW_DAYS)).timestamp()
    prev_start = (now - timedelta(days=2 * WINDOW_DAYS)).timestamp()
    real = [c for c in commits if c.files_changed > 0]
    empty = len(commits) - len(real)
    recent = [c for c in real if c.timestamp >= window_start]
    previous = [c for c in real if prev_start <= c.timestamp < window_start]
    authors = Counter(c.author_email for c in recent)

    merged_prs = open_prs = None
    if pulls is not None:
        border = now - timedelta(days=WINDOW_DAYS)
        merged_prs = sum(1 for p in pulls if str(p.get("status")) == "merged" and (parse_dt(p.get("updated_at")) or border) > border)
        open_prs = sum(1 for p in pulls if str(p.get("status")) == "open")

    last_release_days = None
    published = []
    if releases is not None:
        published = [r for r in releases if str(r.get("status") or "published") == "published"]
        dates = [parse_dt(r.get("released_at") or r.get("created_at")) for r in published]
        dates = [d for d in dates if d]
        if dates:
            last_release_days = days_between(max(dates), now)

    head = commits[0] if commits else None
    return ActivityFacts(
        history_available=True,
        days_since_last_commit=days_between(last_commit, now),
        commits_per_week_last90d=len(recent) / (WINDOW_DAYS / 7),
        active_authors_last90d=len(authors),
        merged_prs_last90d=merged_prs,
        days_since_last_release=last_release_days,
        releases_available=releases is not None,
        commits_last90d=len(recent),
        empty_commits_excluded=empty,
        commits_prev90d=len(previous),
        top_author_share=round(authors.most_common(1)[0][1] / len(recent), 2) if recent else None,
        contributors_total=None if contributors is None else len(contributors),
        open_prs=open_prs,
        releases_total=len(published),
        last_commit_evidence=Evidence("commit", head.sha[:10], commit_url(web_url, head.sha)) if head else None,
    )
