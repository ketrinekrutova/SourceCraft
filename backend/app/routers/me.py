from fastapi import APIRouter

router = APIRouter(tags=["me"])


@router.get("/me/repos")
async def list_my_repos():
    """README 4.3, п.1: список репозиториев, доступных авторизованному пользователю.
    Блокер: эндпоинта для этого нет в swagger, гипотеза org=username не подтверждена — CHECK.md B2."""
    raise NotImplementedError
