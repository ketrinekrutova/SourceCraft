"""Очередь задач анализа в БД.

* enqueue - идемпотентна по паре (repo, owner): если задача уже ждёт или выполняется, новая не
  создаётся (защита от дублей при повторных кликах и пересечении с ночным пересчётом).
* claim_next - в Postgres использует SELECT … FOR UPDATE SKIP LOCKED: несколько процессов-воркеров
  на разных машинах разбирают одну очередь без двойной обработки. В SQLite (локальный запуск)
  конкурентность ограничена одним процессом, гонку внутри процесса снимает asyncio.Lock.
* requeue_stale - задачи упавшего воркера (нет heartbeat) возвращаются в очередь."""

import asyncio
import uuid
from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import is_postgres
from ..models import Job
from ..models.base import utcnow

ACTIVE = ("PENDING", "IN_PROGRESS")
MAX_ATTEMPTS = 3
PRIORITY_USER = 10
PRIORITY_MANUAL = 50
PRIORITY_SCHEDULE = 100

_claim_lock = asyncio.Lock()


async def active_job(session: AsyncSession, repo_id: str, owner_user_id: str | None) -> Job | None:
    owner_filter = Job.owner_user_id.is_(None) if owner_user_id is None else Job.owner_user_id == owner_user_id
    return (await session.execute(
        select(Job).where(Job.repo_id == repo_id, owner_filter, Job.status.in_(ACTIVE)).limit(1)
    )).scalar_one_or_none()


async def enqueue(session: AsyncSession, repo_id: str, owner_user_id: str | None, trigger: str,
                  priority: int) -> tuple[Job, bool]:
    """-> (задача, создана_ли_новая)."""
    existing = await active_job(session, repo_id, owner_user_id)
    if existing:
        if priority < existing.priority and existing.status == "PENDING":
            existing.priority = priority
        return existing, False
    job = Job(id=f"job-{uuid.uuid4().hex[:12]}", repo_id=repo_id, owner_user_id=owner_user_id, trigger=trigger,
              priority=priority, status="PENDING", created_at=utcnow())
    session.add(job)
    return job, True


async def claim_next(session: AsyncSession, worker_id: str) -> Job | None:
    async with _claim_lock:
        query = select(Job).where(Job.status == "PENDING").order_by(Job.priority, Job.created_at).limit(1)
        if is_postgres():
            query = query.with_for_update(skip_locked=True)
        job = (await session.execute(query)).scalar_one_or_none()
        if job is None:
            await session.rollback()
            return None
        now = utcnow()
        job.status, job.stage, job.progress = "IN_PROGRESS", "METADATA", 0.0
        job.started_at = job.heartbeat_at = now
        job.worker_id = worker_id
        job.attempts += 1
        await session.commit()
        return job


async def requeue_stale(session: AsyncSession) -> int:
    border = utcnow() - timedelta(seconds=settings.job_stale_after_s)
    stale_cond = (Job.status == "IN_PROGRESS") & or_(Job.heartbeat_at.is_(None), Job.heartbeat_at < border)
    failed = await session.execute(
        update(Job).where(stale_cond, Job.attempts >= MAX_ATTEMPTS)
        .values(status="FAILED", finished_at=utcnow(), error_code="WORKER_LOST",
                error_message="Воркер перестал отвечать; превышено число попыток")
    )
    requeued = await session.execute(
        update(Job).where(stale_cond, Job.attempts < MAX_ATTEMPTS).values(status="PENDING", worker_id=None)
    )
    await session.commit()
    return (requeued.rowcount or 0) + (failed.rowcount or 0)
