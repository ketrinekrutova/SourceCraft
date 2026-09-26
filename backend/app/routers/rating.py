from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Repository
from ..models.base import as_utc
from ..schemas.rating import CatalogSummary, RepositoryPage, RepositorySummary
from ._views import api_error

router = APIRouter(tags=["Ranking"])

SORTS = {"health_score", "likes", "last_activity"}


def _public_catalog():
    return (Repository.visibility == "public") & Repository.in_catalog.is_(True)


@router.get("/repositories", response_model=RepositoryPage)
async def list_repositories(
    language: str | None = None,
    sort_by: str = "health_score",
    order: str = "desc",
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Публичный рейтинг. Только публичные репозитории и только публичные анализы - личные
    результаты (с AppSec по PAT владельца) сюда не попадают. Score - сортировка по умолчанию и
    главный вторичный ключ при любой сортировке: рейтинг не превращается в список популярности."""
    if sort_by not in SORTS or order not in ("asc", "desc"):
        raise api_error(400, "INVALID_SORT", "sort_by: health_score | likes | last_activity; order: asc | desc")
    cond = _public_catalog()
    if language:
        cond = cond & (func.lower(Repository.language) == language.lower())

    activity = func.coalesce(Repository.last_commit_at, Repository.last_updated_at)
    key = {"health_score": Repository.health_score, "likes": Repository.likes, "last_activity": activity}[sort_by]
    primary = nulls_last(key.desc() if order == "desc" else key.asc())
    query = (select(Repository).where(cond)
             .order_by(primary, nulls_last(Repository.health_score.desc()), Repository.likes.desc(), Repository.id)
             .offset((page - 1) * limit).limit(limit))
    rows = (await session.execute(query)).scalars().all()
    total = (await session.execute(select(func.count()).select_from(Repository).where(cond))).scalar_one()

    catalog_total, analyzed_total, last_analyzed = (await session.execute(
        select(func.count(), func.count(Repository.health_score), func.max(Repository.last_analyzed_at))
        .where(_public_catalog())
    )).one()

    items = [
        RepositorySummary(
            id=r.id, name=r.slug, full_name=r.full_name, url=r.web_url, health_score=r.health_score, likes=r.likes,
            language=r.language, last_activity_at=as_utc(r.last_activity_at), last_analyzed_at=as_utc(r.last_analyzed_at),
            status=r.analysis_status or "PENDING", coverage=r.coverage,
        )
        for r in rows
    ]
    return RepositoryPage(items=items, page=page, limit=limit, total=total,
                          summary=CatalogSummary(catalog_total=catalog_total, analyzed_total=analyzed_total,
                                                 last_analyzed_at=as_utc(last_analyzed)))


@router.get("/repositories/languages", response_model=list[str])
async def list_languages(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(Repository.language, func.count()).where(_public_catalog(), Repository.language.is_not(None))
        .group_by(Repository.language).order_by(func.count().desc())
    )).all()
    return [lang for lang, _ in rows]
