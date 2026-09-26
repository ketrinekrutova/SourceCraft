"""Общие для роутеров: ошибки в формате openapi.yaml, сборка ответов, контроль доступа."""

import json
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_utils import decrypt_token
from ..clients.http import SourceError
from ..clients.sourcecraft_api import SourceCraftAPIClient
from ..models import Analysis, Job, Repository, User, UserRepoAccess
from ..models.base import as_utc, utcnow
from ..schemas.analysis import JobInfo, Metric, Metrics, PreviousAnalysis, Recommendation, RepositoryDetail
from ..scoring.aggregate import verdict

API_CATEGORY_KEYS = {"documentation": "documentation", "cicd": "ci_cd", "security": "security",
                     "activity": "activity", "issues": "issues", "code_health": "code_health"}
ACCESS_RECHECK = timedelta(hours=1)


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, detail={"code": code, "message": message})


def parse_scope(scope: str) -> str:
    if scope not in ("public", "personal"):
        raise api_error(400, "INVALID_SCOPE", "scope должен быть public или personal")
    return scope


def job_info(job: Job | None) -> JobInfo | None:
    if job is None:
        return None
    error = {"code": job.error_code, "message": job.error_message} if job.error_code or job.error_message else None
    return JobInfo(job_id=job.id, status=job.status, stage=job.stage, progress=job.progress,
                   created_at=as_utc(job.created_at), finished_at=as_utc(job.finished_at), error=error)


def _metric(cat: dict) -> Metric:
    return Metric(
        score=cat["score"], status="OK" if cat["status"] == "ok" else "NO_DATA", summary=cat["explanation"],
        weight=cat["weight"], base_weight=cat["base_weight"], contribution=cat["contribution"],
        components=cat.get("components", []), details=cat.get("details", {}), evidence=cat.get("evidence", []),
    )


def _recommendation(index: int, rec: dict) -> Recommendation:
    return Recommendation(
        id=f"rec-{index + 1}", priority=rec["priority"].upper(), category=API_CATEGORY_KEYS[rec["category"]],
        title=rec["problem"], description=f"{rec['why_it_matters']}. {rec['action']}.",
        problem=rec["problem"], why_it_matters=rec["why_it_matters"], action=rec["action"], facts=rec.get("facts", ""),
        impact=rec.get("expected_impact"), score_gain=rec.get("score_gain", 0), evidence=rec.get("evidence", []),
    )


def build_detail(repo: Repository, scope: str, analysis: Analysis | None, previous: Analysis | None,
                 latest_job: Job | None) -> RepositoryDetail:
    base = dict(
        id=repo.id, name=repo.slug, full_name=repo.full_name, url=repo.web_url, description=repo.description,
        language=repo.language, likes=repo.likes, visibility=repo.visibility, scope=scope,
        latest_job=job_info(latest_job),
    )
    if analysis is None:
        return RepositoryDetail(**base, health_score=None, verdict="Анализ ещё не выполнялся", status="PENDING",
                                last_analyzed_at=None, metrics=None)
    data = json.loads(analysis.result_json)
    cats = data["categories"]
    return RepositoryDetail(
        **base,
        health_score=analysis.health_score,
        verdict=data.get("verdict") or verdict(analysis.health_score),
        status=analysis.status,
        last_analyzed_at=as_utc(analysis.finished_at),
        methodology_version=analysis.methodology_version,
        coverage=data.get("coverage", 0),
        metrics=Metrics(**{API_CATEGORY_KEYS[k]: _metric(v) for k, v in cats.items()}),
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        recommendations=[_recommendation(i, r) for i, r in enumerate(data.get("recommendations", []))],
        sources=data.get("sources", {}),
        previous=PreviousAnalysis(health_score=previous.health_score, analyzed_at=as_utc(previous.finished_at))
        if previous else None,
    )


async def latest_job(session: AsyncSession, repo_id: str, owner_user_id: str | None) -> Job | None:
    owner = Job.owner_user_id.is_(None) if owner_user_id is None else Job.owner_user_id == owner_user_id
    return (await session.execute(
        select(Job).where(Job.repo_id == repo_id, owner).order_by(Job.created_at.desc()).limit(1)
    )).scalar_one_or_none()


async def get_repo_or_404(session: AsyncSession, repo_id: str) -> Repository:
    repo = await session.get(Repository, repo_id)
    if repo is None:
        raise api_error(404, "REPOSITORY_NOT_FOUND", "Репозиторий не найден")
    return repo


async def ensure_public_view(repo: Repository) -> None:
    if not repo.is_public:
        # Не раскрываем даже факт существования закрытого репозитория.
        raise api_error(404, "REPOSITORY_NOT_FOUND", "Репозиторий не найден")


async def ensure_personal_access(session: AsyncSession, user: User | None, repo: Repository) -> User:
    """Личные данные отдаются только пользователю, чей PAT подтверждённо видит репозиторий.
    Подтверждение старше часа перепроверяется запросом к SourceCraft с его токеном -
    отозванный доступ закрывает и уже посчитанный отчёт (ограничение 11.4 ТЗ)."""
    if user is None:
        raise api_error(401, "UNAUTHORIZED", "Войдите через Я ID")
    access = await session.get(UserRepoAccess, (user.id, repo.id))
    if access is None:
        raise api_error(404, "REPOSITORY_NOT_FOUND", "Репозиторий не найден среди ваших")
    if utcnow() - as_utc(access.verified_at) > ACCESS_RECHECK:
        token = decrypt_token(user.sc_token_encrypted)
        if not token:
            raise api_error(403, "NO_TOKEN", "Добавьте PAT SourceCraft, чтобы открыть личный отчёт")
        try:
            async with SourceCraftAPIClient(token) as api:
                await api.get_repo_by_id(repo.id)
        except SourceError as exc:
            if exc.kind in ("no_access", "not_found"):
                await session.delete(access)
                await session.commit()
                raise api_error(403, "ACCESS_DENIED", "Ваш PAT больше не даёт доступа к этому репозиторию") from exc
            return user  # SourceCraft временно недоступен - не блокируем по последнему подтверждению
        access.verified_at = utcnow()
        await session.commit()
    return user
