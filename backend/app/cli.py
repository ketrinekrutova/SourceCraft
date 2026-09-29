"""Команды для демонстрации и воспроизведения результатов без UI.

  python -m app.cli discover            # обойти каталог открытых репозиториев SourceCraft
  python -m app.cli sweep               # то, что делает ночное расписание: discover + постановка в очередь
  python -m app.cli analyze org/repo    # поставить анализ и выполнить его сразу в этом процессе
  python -m app.cli run-queue           # выполнить все задачи из очереди и выйти
"""

import argparse
import asyncio
import json
import logging
import sys

from sqlalchemy import select

from .db import async_session, init_db
from .models import Job
from .services.analysis import latest_analysis, run_job
from .services.queue import PRIORITY_MANUAL, claim_next, enqueue
from .services.repositories import parse_repo_ref, resolve_public_repo
from .workers.scheduler import discover_catalog, scheduled_sweep

# Консоль Windows по умолчанию в cp1252/cp866 - без этого печать кириллицы падает с UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _analyze(ref: str) -> None:
    parsed = parse_repo_ref(ref)
    if not parsed:
        raise SystemExit(f"Не распознано: {ref}")
    async with async_session() as s:
        repo = await resolve_public_repo(s, *parsed)
        job, _ = await enqueue(s, repo.id, None, "manual", PRIORITY_MANUAL)
        await s.commit()
        repo_id, job_id = repo.id, job.id
    async with async_session() as s:
        job = await s.get(Job, job_id)
        if job.status == "PENDING":
            job.status = "IN_PROGRESS"
            job.attempts += 1
            await s.commit()
    await run_job(job_id)
    async with async_session() as s:
        job = await s.get(Job, job_id)
        analysis = await latest_analysis(s, repo_id, None)
    print(f"job {job_id}: {job.status} {job.error_message or ''}")
    if analysis:
        data = json.loads(analysis.result_json)
        print(f"Repo Health Score: {analysis.health_score} - {data['verdict']} (полнота {data['coverage']:.0%})")
        for name, cat in data["categories"].items():
            score = "Нет данных" if cat["status"] == "no_data" else cat["score"]
            print(f"  {name:14} {str(score):>10}  {cat['explanation']}")
        for rec in data["recommendations"]:
            print(f"  [{rec['priority'].upper():6}] {rec['problem']} → {rec['expected_impact']}")


async def _run_queue() -> None:
    while True:
        async with async_session() as s:
            job = await claim_next(s, "cli")
        if job is None:
            break
        await run_job(job.id)
    async with async_session() as s:
        rows = (await s.execute(select(Job.status))).scalars().all()
    print({status: rows.count(status) for status in set(rows)})


async def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("discover")
    sub.add_parser("sweep")
    sub.add_parser("run-queue")
    analyze = sub.add_parser("analyze")
    analyze.add_argument("repo", help="org/repo или ссылка на репозиторий SourceCraft")
    args = parser.parse_args()

    await init_db()
    if args.cmd == "discover":
        print(await discover_catalog())
    elif args.cmd == "sweep":
        await scheduled_sweep()
    elif args.cmd == "analyze":
        await _analyze(args.repo)
    elif args.cmd == "run-queue":
        await _run_queue()


if __name__ == "__main__":
    asyncio.run(main())
