import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_utils import current_user, decrypt_token
from ..clients.http import SourceError
from ..clients.sourcecraft_api import SourceCraftAPIClient
from ..db import get_session
from ..models import Analysis, Job, Repository, User, UserRepoAccess
from ..models.base import as_utc, utcnow
from ..schemas.analysis import AnalyzeRequest, HistoryPoint, JobAccepted, RepositoryDetail
from ..schemas.analysis import Job as JobSchema
from ..services.analysis import latest_analysis
from ..services.queue import PRIORITY_MANUAL, PRIORITY_USER, enqueue
from ..services.repositories import ResolveError, parse_repo_ref, resolve_public_repo, upsert_repository
from ._views import (
    api_error,
    build_detail,
    ensure_personal_access,
    ensure_public_view,
    get_repo_or_404,
    latest_job,
    parse_scope,
)

router = APIRouter(tags=["Analysis"])

# Простой лимит ручных запусков на IP (429 из openapi.yaml): защищает квоту SourceCraft API.
RATE_WINDOW_S, RATE_MAX = 600, 20
_launches: dict[str, deque] = defaultdict(deque)


def _check_rate(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    q = _launches[key]
    while q and now - q[0] > RATE_WINDOW_S:
        q.popleft()
    if len(q) >= RATE_MAX:
        raise api_error(429, "RATE_LIMIT_EXCEEDED", "Слишком много запусков анализа, попробуйте позже")
    q.append(now)


def _accepted(job: Job, scope: str) -> JSONResponse:
    body = JobAccepted(job_id=job.id, repository_id=job.repo_id, status=job.status, queued_at=as_utc(job.created_at),
                       status_url=f"/api/v1/jobs/{job.id}", scope=scope)
    return JSONResponse(body.model_dump(mode="json"), status_code=202)


def _owner_scope(scope: str, user: User | None) -> str | None:
    return user.id if scope == "personal" and user else None


@router.get("/repositories/{repo_id}", response_model=RepositoryDetail)
async def get_repository(repo_id: str, scope: str = "public", session: AsyncSession = Depends(get_session),
                         user: User | None = Depends(current_user)):
    """Отчёт по репозиторию. scope=public - публичный анализ (как в рейтинге);
    scope=personal - личный анализ по PAT пользователя (с AppSec), только для него."""
    scope = parse_scope(scope)
    repo = await get_repo_or_404(session, repo_id)
    if scope == "public":
        await ensure_public_view(repo)
    else:
        await ensure_personal_access(session, user, repo)
    owner = _owner_scope(scope, user)
    analysis = await latest_analysis(session, repo.id, owner)
    previous = await latest_analysis(session, repo.id, owner, offset=1) if analysis else None
    job = await latest_job(session, repo.id, owner)
    return build_detail(repo, scope, analysis, previous, job)


@router.get("/repositories/{repo_id}/history", response_model=list[HistoryPoint])
async def get_history(repo_id: str, scope: str = "public", session: AsyncSession = Depends(get_session),
                      user: User | None = Depends(current_user)):
    scope = parse_scope(scope)
    repo = await get_repo_or_404(session, repo_id)
    if scope == "public":
        await ensure_public_view(repo)
    else:
        await ensure_personal_access(session, user, repo)
    owner = _owner_scope(scope, user)
    cond = Analysis.owner_user_id.is_(None) if owner is None else Analysis.owner_user_id == owner
    rows = (await session.execute(
        select(Analysis).where(Analysis.repo_id == repo.id, cond).order_by(Analysis.finished_at.desc()).limit(30)
    )).scalars().all()
    return [HistoryPoint(analyzed_at=as_utc(a.finished_at), health_score=a.health_score, status=a.status) for a in rows]


@router.post("/repositories/analyze", status_code=202, response_model=JobAccepted)
async def analyze_repository(body: AnalyzeRequest, request: Request, session: AsyncSession = Depends(get_session),
                             user: User | None = Depends(current_user)):
    """Первичный анализ по ссылке. Идемпотентен по репозиторию: если анализ уже в очереди или
    выполняется - возвращается существующая задача, новая не создаётся."""
    scope = parse_scope(body.scope)
    ref = parse_repo_ref(body.repository_url)
    if ref is None:
        raise api_error(400, "INVALID_REPOSITORY_URL", "URL не распознан как репозиторий SourceCraft (ожидается org/repo)")
    org, slug = ref
    _check_rate(request)

    if scope == "personal":
        if user is None:
            raise api_error(401, "UNAUTHORIZED", "Войдите через Я ID")
        token = decrypt_token(user.sc_token_encrypted)
        if not token:
            raise api_error(400, "NO_TOKEN", "Сначала добавьте PAT SourceCraft")
        try:
            async with SourceCraftAPIClient(token) as api:
                data = await api.get_repo(org, slug)
        except SourceError as exc:
            if exc.kind in ("no_access", "not_found"):
                raise api_error(404, "REPOSITORY_NOT_FOUND", "Репозиторий не найден или ваш PAT не даёт к нему доступа") from exc
            raise api_error(502, "SOURCECRAFT_UNAVAILABLE", f"SourceCraft API недоступен: {exc}") from exc
        repo = await upsert_repository(session, data)
        access = await session.get(UserRepoAccess, (user.id, repo.id))
        if access is None:
            session.add(UserRepoAccess(user_id=user.id, repo_id=repo.id, verified_at=utcnow()))
        else:
            access.verified_at = utcnow()
        job, _ = await enqueue(session, repo.id, user.id, "user", PRIORITY_USER)
        await session.commit()
        return _accepted(job, scope)

    repo = await _resolve_public_repo(session, org, slug)
    job, _ = await enqueue(session, repo.id, None, "manual", PRIORITY_MANUAL)
    await session.commit()
    return _accepted(job, scope)


async def _resolve_public_repo(session: AsyncSession, org: str, slug: str) -> Repository:
    try:
        return await resolve_public_repo(session, org, slug)
    except ResolveError as exc:
        raise api_error(exc.status, exc.code, str(exc)) from exc


@router.post("/repositories/{repo_id}/reanalyze", status_code=202, response_model=JobAccepted)
async def reanalyze_repository(repo_id: str, request: Request, scope: str = "public",
                               session: AsyncSession = Depends(get_session), user: User | None = Depends(current_user)):
    """Повторный анализ. last_analyzed_at обновится по завершении задачи, а не в момент запроса."""
    scope = parse_scope(scope)
    repo = await get_repo_or_404(session, repo_id)
    _check_rate(request)
    if scope == "public":
        await ensure_public_view(repo)
        job, _ = await enqueue(session, repo.id, None, "manual", PRIORITY_MANUAL)
    else:
        await ensure_personal_access(session, user, repo)
        job, _ = await enqueue(session, repo.id, user.id, "user", PRIORITY_USER)
    await session.commit()
    return _accepted(job, scope)


@router.get("/jobs/{job_id}", response_model=JobSchema, tags=["Jobs"])
async def get_job(job_id: str, session: AsyncSession = Depends(get_session), user: User | None = Depends(current_user)):
    job = await session.get(Job, job_id)
    if job is None or (job.owner_user_id and (user is None or user.id != job.owner_user_id)):
        raise api_error(404, "JOB_NOT_FOUND", "Задача не найдена")
    error = {"code": job.error_code, "message": job.error_message} if job.error_code or job.error_message else None
    return JobSchema(job_id=job.id, repository_id=job.repo_id, status=job.status, progress=job.progress, stage=job.stage,
                     started_at=as_utc(job.started_at), finished_at=as_utc(job.finished_at), error=error,
                     scope="personal" if job.owner_user_id else "public")
