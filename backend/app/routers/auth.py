from fastapi import APIRouter

router = APIRouter(tags=["auth"])


@router.get("/auth/oauth/login")
async def oauth_login():
    """Редирект на Я ID OAuth. client_id/redirect_uri — из config.settings (CHECK.md A2)."""
    raise NotImplementedError


@router.get("/auth/oauth/callback")
async def oauth_callback(code: str):
    """Обмен code на токен Я ID, затем (способ не проверен) получение SourceCraft PAT пользователя.
    Токен пользователя сохраняется в users.sourcecraft_pat — используется во всех приватных запросах."""
    raise NotImplementedError
