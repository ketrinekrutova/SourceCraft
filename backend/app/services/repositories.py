import asyncio
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients import git_client as git
from ..clients.http import SourceError
from ..clients.sourcecraft_api import SourceCraftAPIClient
from ..config import settings
from ..models import Analysis, Job, Repository, UserRepoAccess
from ..normalizers.common import parse_dt

# https://sourcecraft.dev/org/repo[/...], https://git.sourcecraft.dev/org/repo.git, org/repo
URL_RE = re.compile(
    r"^(?:https?://)?(?:(?:git\.)?sourcecraft\.dev/)?(?P<org>[A-Za-z0-9][\w.\-]*)/(?P<repo>[\w.\-]+?)(?:\.git)?(?:[/?#].*)?$"
)


def parse_repo_ref(value: str) -> tuple[str, str] | None:
    match = URL_RE.match(value.strip())
    if not match:
        return None
    return match.group("org"), match.group("repo")


def likes_from_api(data: dict[str, Any]) -> int:
    """«Рейтинг лайков» - сумма реакций (like / heart / diamond) из Repository.rating."""
    counts = ((data.get("rating") or {}).get("reaction_counts")) or []
    total = 0
    for c in counts:
        if str(c.get("type")) != "none":
            try:
                total += int(c.get("count") or 0)
            except (TypeError, ValueError):
                pass
    return total


PLACEHOLDER_PREFIX = "sc:"


async def _drop_placeholders(session: AsyncSession, org: str, slug: str, real_id: str) -> None:
    """Запись, созданная без API (id = sc:org:repo), заменяется настоящей при первом ответе API."""
    rows = (await session.execute(
        select(Repository).where(Repository.org_slug == org, Repository.slug == slug, Repository.id != real_id)
    )).scalars().all()
    for row in rows:
        for model in (Analysis, Job, UserRepoAccess):
            await session.execute(delete(model).where(model.repo_id == row.id))
        await session.delete(row)
    if rows:
        await session.flush()


async def placeholder_repository(session: AsyncSession, org: str, slug: str) -> Repository | None:
    """Режим без сервисного PAT: API недоступен, но публичный репозиторий можно проанализировать
    по git (документация, активность, code health); CI/Issues будут «Нет данных».

    Репозиторий уже может быть в базе под настоящим id из API (каталог, личный анализ) - тогда
    берём его: вторая запись с тем же org/slug нарушила бы уникальный индекс."""
    row = (await session.execute(
        select(Repository).where(Repository.org_slug == org, Repository.slug == slug)
    )).scalar_one_or_none()
    if row:
        return row
    repo_id = f"{PLACEHOLDER_PREFIX}{org}:{slug}"
    clone_url = f"{settings.sourcecraft_git_base_url.rstrip('/')}/{org}/{slug}.git"
    if not await asyncio.to_thread(git.ls_remote, clone_url):
        return None
    row = Repository(id=repo_id, org_slug=org, slug=slug, clone_url=clone_url, visibility="public",
                     web_url=f"{settings.sourcecraft_web_base_url.rstrip('/')}/{org}/{slug}")
    session.add(row)
    return row


async def upsert_repository(session: AsyncSession, data: dict[str, Any], in_catalog: bool | None = None) -> Repository:
    repo_id = str(data["id"])
    org = str(((data.get("organization") or {}).get("slug")) or "")
    slug = str(data.get("slug") or data.get("name") or "")
    await _drop_placeholders(session, org, slug, repo_id)
    row = await session.get(Repository, repo_id)
    if row is None:
        row = Repository(id=repo_id, org_slug=org, slug=slug, web_url="")
        session.add(row)
    row.org_slug = org or row.org_slug
    row.slug = slug or row.slug
    row.description = data.get("description") or None
    row.web_url = data.get("web_url") or f"{settings.sourcecraft_web_base_url.rstrip('/')}/{row.org_slug}/{row.slug}"
    row.clone_url = ((data.get("clone_url") or {}).get("https")) or row.clone_url
    row.default_branch = data.get("default_branch") or row.default_branch
    row.language = ((data.get("language") or {}).get("name")) or None
    row.visibility = str(data.get("visibility") or "public")
    row.is_empty = bool(data.get("is_empty"))
    row.likes = likes_from_api(data)
    rating_value = (data.get("rating") or {}).get("value")
    row.rating_value = float(rating_value) if rating_value is not None else None
    row.last_updated_at = parse_dt(data.get("last_updated")) or row.last_updated_at
    if in_catalog is not None:
        row.in_catalog = in_catalog
    return row


class ResolveError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code = status, code


async def resolve_public_repo(session: AsyncSession, org: str, slug: str) -> Repository:
    """Найти открытый репозиторий: через API по сервисному PAT, а если API недоступен
    (PAT не задан или отклонён) - по анонимному git (режим без токена)."""
    if settings.sourcecraft_service_pat:
        data = None
        try:
            async with SourceCraftAPIClient(settings.sourcecraft_service_pat) as api:
                data = await api.get_repo(org, slug)
        except SourceError as exc:
            if exc.kind == "not_found":
                raise ResolveError(404, "REPOSITORY_NOT_FOUND", "Репозиторий не найден в SourceCraft") from exc
            if exc.kind != "no_access":
                raise ResolveError(502, "SOURCECRAFT_UNAVAILABLE", f"SourceCraft API недоступен: {exc}") from exc
        if data is not None:
            if str(data.get("visibility") or "public") != "public":
                raise ResolveError(400, "NOT_PUBLIC", "Репозиторий закрытый: войдите через Я ID и запустите личный анализ")
            return await upsert_repository(session, data)
    repo = await placeholder_repository(session, org, slug)
    if repo is None:
        raise ResolveError(404, "REPOSITORY_NOT_FOUND", "Открытый репозиторий не найден в SourceCraft")
    if repo.visibility != "public":
        raise ResolveError(400, "NOT_PUBLIC", "Репозиторий закрытый: войдите через Я ID и запустите личный анализ")
    return repo
