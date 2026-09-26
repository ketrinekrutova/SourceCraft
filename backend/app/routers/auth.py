"""Вход через Я ID (OAuth 2.0, authorization code).

Я ID даёт личность пользователя и защищённый личный кабинет; доступ к данным SourceCraft
пользователь даёт отдельно - своим PAT (ответы организаторов 18.09 и 22.09). OAuth-токен Яндекса
после получения профиля не сохраняется."""

import secrets
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_utils import STATE_COOKIE, clear_session, current_user, set_session, sign, unsign
from ..config import settings
from ..db import get_session
from ..models import User
from ._views import api_error
from .user import me_view

router = APIRouter(tags=["Auth"])

YA_AUTHORIZE = "https://oauth.yandex.ru/authorize"
YA_TOKEN = "https://oauth.yandex.ru/token"
YA_INFO = "https://login.yandex.ru/info"


def _frontend(path: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}{path}"


@router.get("/auth/yandex/login")
async def yandex_login():
    if not settings.ya_id_client_id:
        raise api_error(503, "YANDEX_ID_NOT_CONFIGURED", "OAuth-приложение Я ID не настроено (YA_ID_CLIENT_ID)")
    state = secrets.token_urlsafe(24)
    params = {"response_type": "code", "client_id": settings.ya_id_client_id,
              "redirect_uri": settings.ya_id_redirect_uri, "state": state}
    response = RedirectResponse(f"{YA_AUTHORIZE}?{urlencode(params)}")
    response.set_cookie(STATE_COOKIE, sign({"state": state}, salt="oauth-state"), max_age=600, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/")
    return response


@router.get("/auth/yandex/callback")
async def yandex_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None,
                          session: AsyncSession = Depends(get_session)):
    if error or not code:
        return RedirectResponse(_frontend("/my-repositories?auth_error=denied"))
    saved = unsign(request.cookies.get(STATE_COOKIE, ""), max_age=600, salt="oauth-state")
    if not saved or saved.get("state") != state:
        return RedirectResponse(_frontend("/my-repositories?auth_error=state"))

    async with httpx.AsyncClient(timeout=15) as http:
        token_resp = await http.post(YA_TOKEN, data={
            "grant_type": "authorization_code", "code": code,
            "client_id": settings.ya_id_client_id, "client_secret": settings.ya_id_client_secret,
        })
        if token_resp.status_code != 200:
            return RedirectResponse(_frontend("/my-repositories?auth_error=token"))
        access_token = token_resp.json().get("access_token")
        info_resp = await http.get(YA_INFO, params={"format": "json"}, headers={"Authorization": f"OAuth {access_token}"})
        if info_resp.status_code != 200:
            return RedirectResponse(_frontend("/my-repositories?auth_error=profile"))
        info = info_resp.json()

    user = await _upsert_user(session, str(info["id"]), info.get("login"), info.get("display_name") or info.get("real_name"),
                              f"https://avatars.yandex.net/get-yapic/{info['default_avatar_id']}/islands-68"
                              if info.get("default_avatar_id") and not info.get("is_avatar_empty") else None)
    await session.commit()
    response = RedirectResponse(_frontend("/my-repositories"))
    response.delete_cookie(STATE_COOKIE, path="/")
    set_session(response, user.id)
    return response


async def _upsert_user(session: AsyncSession, yandex_id: str, login: str | None, name: str | None,
                       avatar: str | None) -> User:
    user = (await session.execute(select(User).where(User.yandex_id == yandex_id))).scalar_one_or_none()
    if user is None:
        user = User(id=uuid.uuid4().hex, yandex_id=yandex_id)
        session.add(user)
    user.login, user.display_name, user.avatar_url = login, name or login, avatar
    return user


@router.post("/auth/dev-login")
async def dev_login(session: AsyncSession = Depends(get_session)):
    """Только для локальной разработки (DEV_LOGIN_ENABLED=true), пока OAuth-приложение Я ID не
    зарегистрировано. В продакшене выключено."""
    if not settings.dev_login_enabled:
        raise api_error(404, "NOT_FOUND", "Not found")
    user = await _upsert_user(session, "dev-user", "developer", "Локальный разработчик", None)
    await session.commit()
    response = JSONResponse({"authenticated": True, "user": me_view(user).model_dump()})
    set_session(response, user.id)
    return response


@router.get("/auth/me")
async def auth_me(user: User | None = Depends(current_user)):
    return {
        "authenticated": user is not None,
        "user": me_view(user) if user else None,
        "yandex_id_configured": bool(settings.ya_id_client_id),
        "dev_login_enabled": settings.dev_login_enabled,
    }


@router.post("/auth/logout", status_code=204)
async def logout():
    response = Response(status_code=204)
    clear_session(response)
    return response
