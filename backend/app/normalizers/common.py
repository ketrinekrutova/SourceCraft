from datetime import datetime, timezone
from urllib.parse import quote


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def days_between(earlier: datetime | None, later: datetime) -> float | None:
    if earlier is None:
        return None
    return max(0.0, (later - earlier).total_seconds() / 86400)


# Все шаблоны веб-ссылок SourceCraft - только здесь. Проверить шаблон заранее нельзя (SPA
# отвечает 200 на любой путь), поэтому если формат изменится - править в одном месте.

def file_url(web_url: str, path: str, line: int | None = None) -> str:
    url = f"{web_url.rstrip('/')}/browse/{quote(path)}"
    return f"{url}#L{line}" if line else url


def issue_url(web_url: str, slug: str) -> str:
    return f"{web_url.rstrip('/')}/issues/{quote(slug)}"


def pull_url(web_url: str, slug: str) -> str:
    return f"{web_url.rstrip('/')}/pulls/{quote(slug)}"


def run_url(web_url: str, slug: str) -> str:
    return f"{web_url.rstrip('/')}/cicd/runs/{quote(slug)}"


def commit_url(web_url: str, sha: str) -> str:
    return f"{web_url.rstrip('/')}/commit/{sha}"


def security_url(web_url: str) -> str:
    return f"{web_url.rstrip('/')}/security"
