"""Выполнение одной задачи анализа.

Устойчивость к сбоям (ТЗ 6): если анализ упал целиком, предыдущий результат не затирается -
в БД остаётся прошлый Analysis, а задача получает статус FAILED с причиной; страница показывает
«анализ не обновлён» и дату последнего успешного расчёта."""

import asyncio
import contextlib
import json
import logging

from sqlalchemy import delete, select

from ..auth_utils import decrypt_token
from ..clients.git_client import GitAuth
from ..clients.http import SourceError
from ..clients.sourcecraft_api import SourceCraftAPIClient
from ..config import settings
from ..db import async_session
from ..models import Analysis, Job, Repository, User, UserRepoAccess
from ..models.base import utcnow
from ..scoring.engine import evaluate
from ..scoring.result import METHODOLOGY_VERSION
from .collector import CollectContext, collect, repo_ref_from_row
from .repositories import upsert_repository
from .serialize import result_to_dict

log = logging.getLogger(__name__)


class JobFailed(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


async def _update_job(job_id: str, **values) -> None:
    async with async_session() as s:
        job = await s.get(Job, job_id)
        if job is None:
            return
        for key, value in values.items():
            setattr(job, key, value)
        job.heartbeat_at = utcnow()
        await s.commit()


async def _heartbeat(job_id: str) -> None:
    while True:
        await asyncio.sleep(60)
        await _update_job(job_id)


async def run_job(job_id: str) -> None:
    async with async_session() as s:
        job = await s.get(Job, job_id)
        if job is None:
            return
        repo = await s.get(Repository, job.repo_id)
        user = await s.get(User, job.owner_user_id) if job.owner_user_id else None
        started_at = job.started_at or utcnow()

    heartbeat = asyncio.create_task(_heartbeat(job_id))
    try:
        if repo is None:
            raise JobFailed("REPOSITORY_NOT_FOUND", "Репозиторий удалён из базы сервиса")
        ctx = await _build_context(repo, user)

        async def progress(stage: str, value: float):
            await _update_job(job_id, stage=stage, progress=value)

        ctx.progress = progress
        collected = await asyncio.wait_for(collect(ctx), timeout=settings.clone_timeout_s + 900)
        result = evaluate(collected.facts)
        payload = result_to_dict(result, ctx.scope, collected.sources)
        status = "PARTIAL" if collected.partial else "COMPLETED"

        async with async_session() as s:
            analysis = Analysis(
                repo_id=repo.id, owner_user_id=job_owner(user), job_id=job_id, status=status,
                health_score=result.score, verdict=payload["verdict"], methodology_version=METHODOLOGY_VERSION,
                result_json=json.dumps(payload, ensure_ascii=False, default=str), started_at=started_at, finished_at=utcnow(),
            )
            s.add(analysis)
            row = await s.get(Repository, repo.id)
            if row is not None:
                if collected.last_commit_at:
                    row.last_commit_at = collected.last_commit_at
                if user is None:
                    row.health_score, row.coverage = result.score, round(result.coverage, 3)
                    row.last_analyzed_at, row.analysis_status = analysis.finished_at, status
            await s.flush()
            job = await s.get(Job, job_id)
            job.status, job.stage, job.progress = status, None, 1.0
            job.finished_at = utcnow()
            job.analysis_id = analysis.id
            job.error_code = None
            job.error_message = None if status == "COMPLETED" else _partial_message(collected.sources)
            await s.commit()
        log.info("job %s %s: %s/%s score=%s", job_id, status, repo.org_slug, repo.slug, result.score)
    except Exception as exc:  # noqa: BLE001 - любая ошибка = FAILED с причиной, прошлый результат сохраняется
        code = exc.code if isinstance(exc, JobFailed) else ("TIMEOUT" if isinstance(exc, asyncio.TimeoutError) else "ANALYSIS_FAILED")
        if isinstance(exc, JobFailed):
            log.warning("job %s: %s", job_id, exc)
        else:
            log.exception("job %s failed", job_id)
        await _update_job(job_id, status="FAILED", stage=None, finished_at=utcnow(), error_code=code,
                          error_message=str(exc)[:1000] or type(exc).__name__)
        if user is None and repo is not None:
            async with async_session() as s:
                row = await s.get(Repository, repo.id)
                if row is not None:
                    row.analysis_status = "FAILED"  # Score остаётся прежним - «анализ не обновлён»
                    await s.commit()
    finally:
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat


def job_owner(user: User | None) -> str | None:
    return user.id if user else None


def _partial_message(sources: dict[str, str]) -> str:
    failed = [f"{k}: {v[len('error: '):]}" for k, v in sources.items() if v.startswith("error")]
    return "Часть источников недоступна: " + "; ".join(failed)[:900]


async def _build_context(repo: Repository, user: User | None) -> CollectContext:
    if user is None:
        if not repo.is_public:
            raise JobFailed("NOT_PUBLIC", "Закрытый репозиторий нельзя анализировать в публичном режиме")
        token = settings.sourcecraft_service_pat or None
        if token:  # без PAT API отвечает 401; метаданные уже пришли из открытого каталога
            await _refresh_metadata(repo, token, public=True)
        return CollectContext(repo=repo_ref_from_row(repo), scope="public", api_token=token)

    token = decrypt_token(user.sc_token_encrypted)
    if not token:
        raise JobFailed("NO_TOKEN", "Добавьте PAT SourceCraft в разделе «Мои репозитории»")
    await _refresh_metadata(repo, token, public=False, user_id=user.id)
    auth = GitAuth(token=token, username=user.sc_username)
    return CollectContext(repo=repo_ref_from_row(repo), scope="personal", api_token=token, user_token=token, git_auth=auth)


async def _refresh_metadata(repo: Repository, token: str | None, public: bool, user_id: str | None = None) -> None:
    """Актуальные лайки/язык/видимость перед анализом. Для личного анализа это же - проверка,
    что PAT пользователя всё ещё видит репозиторий (иначе закрытые данные не собираем)."""
    if repo.id.startswith("sc:"):
        return  # запись создана без API (сервисный PAT не настроен) - метаданные недоступны
    try:
        async with SourceCraftAPIClient(token) as api:
            data = await api.get_repo_by_id(repo.id)
    except SourceError as exc:
        if not public and exc.kind in ("no_access", "not_found"):
            async with async_session() as s:
                await s.execute(delete(UserRepoAccess).where(UserRepoAccess.user_id == user_id,
                                                             UserRepoAccess.repo_id == repo.id))
                await s.commit()
            raise JobFailed("ACCESS_DENIED", "PAT больше не даёт доступа к этому репозиторию") from exc
        if public and exc.kind == "not_found":
            async with async_session() as s:
                row = await s.get(Repository, repo.id)
                if row:
                    row.in_catalog = False
                await s.commit()
            raise JobFailed("REPOSITORY_NOT_FOUND", "Репозиторий не найден в SourceCraft") from exc
        log.warning("metadata refresh failed for %s: %s", repo.id, exc)
        return
    async with async_session() as s:
        row = await upsert_repository(s, data)
        await s.commit()
        repo.visibility, repo.is_empty, repo.clone_url = row.visibility, row.is_empty, row.clone_url
    if public and repo.visibility != "public":
        raise JobFailed("NOT_PUBLIC", "Репозиторий стал закрытым и исключён из публичного рейтинга")


async def latest_analysis(session, repo_id: str, owner_user_id: str | None, offset: int = 0) -> Analysis | None:
    owner = Analysis.owner_user_id.is_(None) if owner_user_id is None else Analysis.owner_user_id == owner_user_id
    return (await session.execute(
        select(Analysis).where(Analysis.repo_id == repo_id, owner)
        .order_by(Analysis.finished_at.desc(), Analysis.id.desc()).offset(offset).limit(1)
    )).scalar_one_or_none()

