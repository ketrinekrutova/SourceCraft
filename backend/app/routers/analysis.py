from fastapi import APIRouter

from ..schemas.analysis import RepositoryDetail

router = APIRouter(tags=["analysis"])


@router.get("/repos/{repo_id}/analysis", response_model=RepositoryDetail)
async def get_analysis(repo_id: str):
    """README 4.2: итоговый Score, разбивка по категориям, рекомендации, дата анализа."""
    raise NotImplementedError


@router.post("/repos/{repo_id}/reanalyze", status_code=202)
async def trigger_reanalyze(repo_id: str):
    """Ставит full-pass задачу в очередь (см. workers/full_pass.py). Для приватных репозиториев —
    проверка прав пользователя обязательна до постановки в очередь (README 4.3)."""
    raise NotImplementedError
