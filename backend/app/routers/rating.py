from fastapi import APIRouter

from ..schemas.rating import RepositoryPage

router = APIRouter(tags=["rating"])


@router.get("/rating", response_model=RepositoryPage)
async def get_rating(language: str | None = None, sort_by: str = "score", page_token: str | None = None):
    """README 4.1: рейтинг открытых репозиториев, фильтр по языку, сортировка по score/лайкам/активности.
    Реализация — Фаза 5, после наполнения repositories/category_scores реальными данными."""
    raise NotImplementedError
