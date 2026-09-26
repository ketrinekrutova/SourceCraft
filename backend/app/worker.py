"""Отдельный процесс-воркер: `python -m app.worker`.

Для горизонтального масштабирования запускается в нескольких экземплярах рядом с API
(в API тогда RUN_WORKER=false). Планировщик включается только в одном из процессов
(SCHEDULER_ENABLED=true), остальные лишь разбирают очередь."""

import asyncio
import logging
import signal

from .config import settings
from .db import init_db
from .workers.worker import run_workers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    await init_db()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows
            pass
    scheduler = None
    if settings.scheduler_enabled:
        from .workers.scheduler import start_scheduler

        scheduler = start_scheduler()
    try:
        await run_workers(settings.worker_concurrency, stop)
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
