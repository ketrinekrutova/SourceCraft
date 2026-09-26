"""Периодический пересчёт (ТЗ 6).

Расписание: SCHEDULE_CRON (по умолчанию `0 3 * * *` - раз в сутки ночью по UTC):
  1. discover_catalog - обход каталога GET /repos (все открытые репозитории SourceCraft),
     обновление метаданных, пометка исчезнувших из каталога;
  2. schedule_recalculation - постановка в очередь всех публичных репозиториев, чей последний
     анализ старше RECALC_INTERVAL_HOURS (по умолчанию 24 ч). Ручные запуски пользователей имеют
     более высокий приоритет и обгоняют ночной пересчёт.

Почему сутки: код публичных проектов меняется медленно, а полный обход каталога при лимите
10 rps занимает часы - более частый пересчёт не даст новой информации, но съест квоту API."""

import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select, update

from ..clients.sourcecraft_api import SourceCraftAPIClient
from ..clients.sourcecraft_web import SourceCraftWebCatalog
from ..config import settings
from ..db import async_session
from ..models import Analysis, Job, Repository
from ..models.base import utcnow
from ..services.queue import ACTIVE, PRIORITY_SCHEDULE, enqueue
from ..services.repositories import upsert_repository

log = logging.getLogger(__name__)


def _catalog_source():
    """Официальный API по PAT команды, а без токена - открытый каталог веб-интерфейса SourceCraft
    (sourcecraft.dev/find/repositories), см. clients/sourcecraft_web.py."""
    if settings.sourcecraft_service_pat:
        return SourceCraftAPIClient(settings.sourcecraft_service_pat), "api.sourcecraft.tech"
    return SourceCraftWebCatalog(), "sourcecraft.dev/find/repositories"


async def discover_catalog() -> int:
    seen = 0
    started = utcnow()
    source, name = _catalog_source()
    log.info("discovery: обход каталога открытых репозиториев через %s", name)
    async with source:
        async with async_session() as s:
            async for data in source.iter_public_repos():
                if str(data.get("visibility") or "public") != "public":
                    continue
                row = await upsert_repository(s, data, in_catalog=True)
                row.catalog_seen_at = started
                seen += 1
                if seen % 200 == 0:
                    await s.commit()
                    log.info("discovery: %d repositories", seen)
                if settings.discovery_max_repos and seen >= settings.discovery_max_repos:
                    break
            complete = not settings.discovery_max_repos or seen < settings.discovery_max_repos
            if complete and seen:
                # Полный обход завершён: всё публичное, что не встретилось, пропало из каталога.
                await s.execute(update(Repository)
                                .where(Repository.visibility == "public", ~Repository.id.startswith("sc:"),
                                       (Repository.catalog_seen_at.is_(None)) | (Repository.catalog_seen_at < started))
                                .values(in_catalog=False))
            await s.commit()
    log.info("discovery finished: %d public repositories", seen)
    return seen


async def schedule_recalculation() -> int:
    border = utcnow() - timedelta(hours=settings.recalc_interval_hours)
    async with async_session() as s:
        last_public = (select(Analysis.repo_id, func.max(Analysis.finished_at).label("last"))
                       .where(Analysis.owner_user_id.is_(None)).group_by(Analysis.repo_id).subquery())
        active = select(Job.repo_id).where(Job.owner_user_id.is_(None), Job.status.in_(ACTIVE))
        rows = (await s.execute(
            select(Repository.id)
            .outerjoin(last_public, last_public.c.repo_id == Repository.id)
            .where(Repository.visibility == "public", Repository.in_catalog.is_(True),
                   Repository.id.not_in(active),
                   (last_public.c.last.is_(None)) | (last_public.c.last < border))
            # Сначала ни разу не анализированные, среди них - самые популярные (так рейтинг быстрее
            # наполняется значимыми проектами), затем самые давно пересчитанные.
            .order_by(last_public.c.last.is_(None).desc(), last_public.c.last, Repository.likes.desc(), Repository.id)
        )).scalars().all()
        for repo_id in rows:
            await enqueue(s, repo_id, None, "schedule", PRIORITY_SCHEDULE)
        await s.commit()
    log.info("scheduled %d repositories for recalculation", len(rows))
    return len(rows)


async def scheduled_sweep() -> None:
    try:
        await discover_catalog()
    except Exception:  # noqa: BLE001 - недоступность каталога не должна отменять пересчёт известных репозиториев
        log.exception("catalog discovery failed")
    await schedule_recalculation()


async def initial_sweep_if_empty() -> None:
    """Первый запуск стенда: не ждать ночного расписания - сразу обойти каталог и поставить
    все открытые репозитории в очередь, чтобы рейтинг наполнялся без ручных действий."""
    async with async_session() as s:
        known = (await s.execute(
            select(func.count()).select_from(Repository)
            .where(Repository.visibility == "public", ~Repository.id.startswith("sc:"))
        )).scalar_one()
    if known == 0:
        log.info("каталог пуст - первичный обход открытых репозиториев SourceCraft")
        await scheduled_sweep()


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(scheduled_sweep, CronTrigger.from_crontab(settings.schedule_cron, timezone="UTC"),
                      id="sweep", max_instances=1, coalesce=True, misfire_grace_time=3600)
    scheduler.add_job(initial_sweep_if_empty, id="initial-sweep", max_instances=1)  # один раз при старте
    scheduler.start()
    return scheduler
