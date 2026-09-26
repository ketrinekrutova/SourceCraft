"""Личный кабинет: PAT SourceCraft, организации и список доступных репозиториев.

Эндпоинта «все репозитории пользователя» в выгрузке API нет; организаторы предложили (17–18.09)
брать репозитории организаций (ListOrganizationRepositories) или явный ввод репозитория.
Поэтому список = личное пространство (org = username) + организации, указанные пользователем +
репозитории, которые он уже анализировал. Любой другой доступный ему репозиторий можно добавить
по ссылке - права всё равно проверяет SourceCraft по его PAT."""

import json
import re

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_utils import decrypt_token, encrypt_token, require_user
from ..clients.http import SourceError
from ..clients.sourcecraft_api import SourceCraftAPIClient
from ..db import get_session
from ..models import Analysis, Repository, User, UserRepoAccess
from ..models.base import as_utc, utcnow
from ..normalizers.common import parse_dt
from ..schemas.user import Me, OrgsRequest, TokenRequest, UserRepository, UserRepositoryList
from ..services.repositories import likes_from_api
from ._views import api_error

router = APIRouter(tags=["User"])
ORG_RE = re.compile(r"^[A-Za-z0-9][\w.\-]{0,99}$")


def _orgs(user: User) -> list[str]:
    try:
        return list(json.loads(user.sc_orgs_json or "[]"))
    except ValueError:
        return []


def me_view(user: User) -> Me:
    return Me(id=user.id, login=user.login, display_name=user.display_name, avatar_url=user.avatar_url,
              has_token=bool(user.sc_token_encrypted), sourcecraft_username=user.sc_username, orgs=_orgs(user))


@router.put("/user/token", response_model=Me)
async def set_token(body: TokenRequest, user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    """Проверяем токен запросом GET /user и сохраняем только в зашифрованном виде."""
    token = body.token.strip()
    if not token:
        raise api_error(400, "INVALID_TOKEN", "Пустой токен")
    try:
        async with SourceCraftAPIClient(token) as api:
            profile = await api.get_user()
    except SourceError as exc:
        if exc.kind == "no_access":
            raise api_error(400, "INVALID_TOKEN", "SourceCraft отклонил токен - проверьте PAT и его права") from exc
        raise api_error(502, "SOURCECRAFT_UNAVAILABLE", f"SourceCraft API недоступен: {exc}") from exc
    user = await session.merge(user)
    if user.sc_user_id and user.sc_user_id != str(profile.get("id")):
        # Токен другого аккаунта SourceCraft - старые подтверждения доступа недействительны.
        await session.execute(delete(UserRepoAccess).where(UserRepoAccess.user_id == user.id))
    user.sc_token_encrypted = encrypt_token(token)
    user.sc_user_id = str(profile.get("id") or "") or None
    user.sc_username = profile.get("username") or None
    user.token_updated_at = utcnow()
    await session.commit()
    return me_view(user)


@router.delete("/user/token", response_model=Me)
async def delete_token(user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    user = await session.merge(user)
    user.sc_token_encrypted = None
    user.token_updated_at = utcnow()
    # Без токена права на закрытые репозитории больше не подтверждаются.
    await session.execute(delete(UserRepoAccess).where(UserRepoAccess.user_id == user.id))
    await session.commit()
    return me_view(user)


@router.put("/user/orgs", response_model=Me)
async def set_orgs(body: OrgsRequest, user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    orgs = []
    for raw in body.orgs:
        org = raw.strip().strip("/").split("/")[-1]
        if not org:
            continue
        if not ORG_RE.match(org):
            raise api_error(400, "INVALID_ORG", f"Некорректный slug организации: {raw}")
        if org not in orgs:
            orgs.append(org)
    user = await session.merge(user)
    user.sc_orgs_json = json.dumps(orgs[:20])
    await session.commit()
    return me_view(user)


@router.get("/user/repositories", response_model=UserRepositoryList)
async def list_user_repositories(user: User = Depends(require_user), session: AsyncSession = Depends(get_session)):
    token = decrypt_token(user.sc_token_encrypted)
    if not token:
        raise api_error(400, "NO_TOKEN", "Добавьте PAT SourceCraft, чтобы увидеть свои репозитории")

    orgs = [o for o in [user.sc_username, *_orgs(user)] if o]
    found: dict[str, dict] = {}
    errors = []
    async with SourceCraftAPIClient(token) as api:
        for org in dict.fromkeys(orgs):
            try:
                for data in await api.list_org_repos(org):
                    found[str(data["id"])] = data
            except SourceError as exc:
                errors.append(f"{org}: {'нет доступа или организация не найдена' if exc.kind in ('no_access', 'not_found') else exc}")

    # Уже проанализированные пользователем репозитории (добавленные по ссылке).
    known = (await session.execute(
        select(Repository).join(UserRepoAccess, UserRepoAccess.repo_id == Repository.id)
        .where(UserRepoAccess.user_id == user.id)
    )).scalars().all()
    known_by_id = {r.id: r for r in known}

    last = (await session.execute(
        select(Analysis.repo_id, func.max(Analysis.finished_at))
        .where(Analysis.owner_user_id == user.id).group_by(Analysis.repo_id)
    )).all()
    last_by_repo = dict(last)
    scores = {}
    if last_by_repo:
        rows = (await session.execute(
            select(Analysis).where(Analysis.owner_user_id == user.id, Analysis.repo_id.in_(last_by_repo))
        )).scalars().all()
        for a in rows:
            if a.finished_at == last_by_repo[a.repo_id]:
                scores[a.repo_id] = a

    items: dict[str, UserRepository] = {}
    for repo_id, data in found.items():
        org = ((data.get("organization") or {}).get("slug")) or ""
        slug = data.get("slug") or ""
        visibility = str(data.get("visibility") or "public")
        a = scores.get(repo_id)
        items[repo_id] = UserRepository(
            id=repo_id, name=slug, full_name=f"{org}/{slug}", url=data.get("web_url") or "", private=visibility != "public",
            visibility=visibility, health_score=a.health_score if a else None, likes=likes_from_api(data),
            language=((data.get("language") or {}).get("name")), last_activity_at=parse_dt(data.get("last_updated")),
            last_analyzed_at=as_utc(a.finished_at) if a else None, analyzed=a is not None,
        )
    for repo_id, r in known_by_id.items():
        if repo_id in items:
            continue
        a = scores.get(repo_id)
        items[repo_id] = UserRepository(
            id=r.id, name=r.slug, full_name=r.full_name, url=r.web_url, private=not r.is_public, visibility=r.visibility,
            health_score=a.health_score if a else None, likes=r.likes, language=r.language,
            last_activity_at=as_utc(r.last_activity_at), last_analyzed_at=as_utc(a.finished_at) if a else None,
            analyzed=a is not None,
        )
    ordered = sorted(items.values(), key=lambda i: (not i.analyzed, i.full_name.lower()))
    return UserRepositoryList(items=ordered, orgs_checked=list(dict.fromkeys(orgs)), errors=errors)
