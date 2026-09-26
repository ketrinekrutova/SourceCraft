"""Пул воркеров: забирают задачи из очереди в БД и выполняют анализ.

Масштабирование: `python -m app.worker` можно запустить в любом количестве экземпляров (на Postgres
очередь разбирается через SKIP LOCKED). Внутри процесса - worker_concurrency параллельных задач.
Лимит частоты запросов к SourceCraft действует на процесс: при N процессах выставьте
SOURCECRAFT_API_RPS ≈ 10 / N (лимит организаторов - 10 rps на хост)."""

import asyncio
import contextlib
import logging
import os
import socket

from ..db import async_session
from ..services.analysis import run_job
from ..services.queue import claim_next, requeue_stale

log = logging.getLogger(__name__)
IDLE_SLEEP_S = 3
REQUEUE_EVERY_S = 300


async def _worker(index: int, stop: asyncio.Event) -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{index}"
    while not stop.is_set():
        try:
            async with async_session() as s:
                job = await claim_next(s, worker_id)
        except Exception:  # noqa: BLE001
            log.exception("claim failed")
            job = None
        if job is None:
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=IDLE_SLEEP_S)
            continue
        await run_job(job.id)


async def _janitor(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            async with async_session() as s:
                n = await requeue_stale(s)
            if n:
                log.warning("requeued/failed %d stale jobs", n)
        except Exception:  # noqa: BLE001
            log.exception("requeue failed")
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=REQUEUE_EVERY_S)


async def run_workers(concurrency: int, stop: asyncio.Event) -> None:
    tasks = [asyncio.create_task(_worker(i, stop)) for i in range(concurrency)]
    tasks.append(asyncio.create_task(_janitor(stop)))
    await asyncio.gather(*tasks)
