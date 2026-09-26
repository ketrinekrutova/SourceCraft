"""Общий HTTP-слой для SourceCraft API и AppSec API: лимит частоты на хост, повторы на
временных ошибках и единая классификация отказов источника.

Классификация важна для методики: отказ источника превращается в статус «Нет данных» категории,
а не в 500 всей страницы и не в «плохую оценку» (ТЗ 3.2, ограничение 11.5)."""

import asyncio
import logging
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)


class SourceError(Exception):
    """Источник данных не отдал ответ.

    kind:
      no_access   - 401/403: у токена нет прав (ожидаемо для CI/Issues/AppSec чужих репозиториев)
      not_found   - 404
      unavailable - таймаут, 5xx, исчерпаны повторы на 429
    """

    def __init__(self, kind: str, message: str, status: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.status = status


class RateLimiter:
    """Равномерный лимит запросов в секунду в пределах процесса."""

    def __init__(self, rps: float):
        self._interval = 1.0 / rps if rps > 0 else 0.0
        self._next_at = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if not self._interval:
            return
        async with self._lock:
            now = time.monotonic()
            wait = self._next_at - now
            self._next_at = max(now, self._next_at) + self._interval
        if wait > 0:
            await asyncio.sleep(wait)


_limiters: dict[str, RateLimiter] = {}


def limiter_for(host_key: str, rps: float) -> RateLimiter:
    if host_key not in _limiters:
        _limiters[host_key] = RateLimiter(rps)
    return _limiters[host_key]


class JSONClient:
    MAX_ATTEMPTS = 4

    def __init__(self, base_url: str, token: str | None, limiter: RateLimiter, timeout_s: float):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.AsyncClient(base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_s)
        self._limiter = limiter

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()

    async def get_json(self, path: str, params: Any = None) -> dict[str, Any]:
        last_error = "unknown error"
        for attempt in range(self.MAX_ATTEMPTS):
            await self._limiter.acquire()
            try:
                resp = await self._http.get(path, params=params)
            except httpx.HTTPError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                await asyncio.sleep(min(2**attempt, 10))
                continue

            if resp.status_code == 200:
                return resp.json() if resp.content else {}
            if resp.status_code in (401, 403):
                raise SourceError("no_access", f"{resp.status_code} {path}", resp.status_code)
            if resp.status_code == 404:
                raise SourceError("not_found", f"404 {path}", 404)
            if resp.status_code == 429 or resp.status_code >= 500:
                last_error = f"{resp.status_code} {path}"
                retry_after = resp.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 10)
                await asyncio.sleep(delay)
                continue
            raise SourceError("unavailable", f"{resp.status_code} {path}: {resp.text[:200]}", resp.status_code)
        raise SourceError("unavailable", last_error)
