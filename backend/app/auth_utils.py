"""Сессия пользователя (подписанная cookie) и шифрование сохранённых PAT."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_session
from .models import User

SESSION_COOKIE = "rh_session"
STATE_COOKIE = "rh_oauth_state"

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="rh-session")
_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(f"pat:{settings.secret_key}".encode()).digest()))


def encrypt_token(token: str) -> str:
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        return None  # SECRET_KEY сменился - пользователь просто введёт токен заново


def sign(payload: dict, salt: str = "rh-session") -> str:
    return URLSafeTimedSerializer(settings.secret_key, salt=salt).dumps(payload)


def unsign(value: str, max_age: int, salt: str = "rh-session") -> dict | None:
    try:
        return URLSafeTimedSerializer(settings.secret_key, salt=salt).loads(value, max_age=max_age)
    except BadSignature:
        return None


def set_session(response: Response, user_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, _serializer.dumps({"uid": user_id}), max_age=settings.session_max_age_s,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


async def current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        data = _serializer.loads(raw, max_age=settings.session_max_age_s)
    except BadSignature:
        return None
    return await session.get(User, data.get("uid"))


async def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(401, detail={"code": "UNAUTHORIZED", "message": "Войдите через Я ID"})
    return user
