"""Каталог открытых репозиториев через веб-интерфейс SourceCraft (без токена).

Официальный API (api.sourcecraft.tech) отдаёт каталог GET /repos только с PAT. Страница
sourcecraft.dev/find/repositories («Топ репозиториев») открыта анонимно: браузер получает список
методом listTopRepositories внутреннего gateway (`POST /gateway/root/api/listTopRepositories`,
CSRF-токен из самой страницы). Используем его как запасной источник каталога, когда
SOURCECRAFT_SERVICE_PAT не задан. Ответ приводится к форме Repository официального API, чтобы
дальше работал тот же upsert_repository.

Это внутренний, недокументированный интерфейс: при изменении формата достаточно поправить этот
модуль; при наличии PAT каталог берётся из официального API."""

import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import settings
from .http import SourceError, limiter_for

GATEWAY_METHOD = "/gateway/root/api/listTopRepositories"
CATALOG_PAGE = "/find/repositories"
REACTION_TYPES = {
    "RR_TYPE_POSITIVE_LEVEL_10": "positive_low",
    "RR_TYPE_POSITIVE_LEVEL_20": "positive_medium",
    "RR_TYPE_POSITIVE_LEVEL_30": "positive_high",
}


def to_api_shape(item: dict[str, Any]) -> dict[str, Any]:
    org, slug = item.get("orgSlug") or "", item.get("slug") or item.get("name") or ""
    web = settings.sourcecraft_web_base_url.rstrip("/")
    git = settings.sourcecraft_git_base_url.rstrip("/")
    updated = (item.get("lastUpdated") or {}).get("seconds")
    rating = item.get("rating") or {}
    return {
        "id": str(item["id"]),
        "slug": slug,
        "organization": {"id": item.get("orgId"), "slug": org},
        "description": item.get("description") or None,
        "visibility": "public" if item.get("visibility") == "RESOURCE_PUBLIC" else "private",
        "web_url": f"{web}/{org}/{slug}",
        "clone_url": {"https": f"{git}/{org}/{slug}.git"},
        "default_branch": item.get("defaultBranch"),
        "is_empty": bool(item.get("isEmpty")),
        "language": item.get("language"),
        "rating": {
            "value": rating.get("value"),
            "reaction_counts": [{"type": REACTION_TYPES.get(k, k), "count": v}
                                for k, v in (rating.get("reactions") or {}).items()],
        },
        "last_updated": datetime.fromtimestamp(int(updated), tz=timezone.utc).isoformat() if updated else None,
    }


class SourceCraftWebCatalog:
    def __init__(self):
        self._http = httpx.AsyncClient(base_url=settings.sourcecraft_web_base_url.rstrip("/"),
                                       timeout=settings.http_timeout_s, follow_redirects=True)
        self._limiter = limiter_for("sourcecraft_web", min(settings.sourcecraft_api_rps, 5))
        self._csrf: str | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._http.aclose()

    async def _token(self, refresh: bool = False) -> str:
        if self._csrf and not refresh:
            return self._csrf
        page = await self._http.get(CATALOG_PAGE)
        match = re.search(r'"csrfToken":"([^"]+)"', page.text)
        if not match:
            raise SourceError("unavailable", "CSRF-токен на странице каталога не найден")
        self._csrf = match.group(1)
        return self._csrf

    async def _page(self, page_token: str | None) -> dict[str, Any]:
        body = {"pageSize": "100", **({"pageToken": page_token} if page_token else {})}
        for attempt in range(3):
            await self._limiter.acquire()
            resp = await self._http.post(GATEWAY_METHOD, json=body,
                                         headers={"x-csrf-token": await self._token(refresh=attempt > 0)})
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code not in (401, 403, 419, 429) and resp.status_code < 500:
                break
        raise SourceError("unavailable", f"каталог SourceCraft: {resp.status_code} {resp.text[:200]}", resp.status_code)

    async def iter_public_repos(self) -> AsyncIterator[dict[str, Any]]:
        token = None
        while True:
            data = await self._page(token)
            items = data.get("repositories") or []
            for item in items:
                if item.get("id"):
                    yield to_api_shape(item)
            token = data.get("nextPageToken")
            if not token or not items:
                break
