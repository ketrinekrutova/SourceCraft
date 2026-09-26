"""Клиент api.sourcecraft.tech. Пути, параметры и поля сверены с документацией https://api.sourcecraft.tech/docs/index.html.
Авторизация во всех запросах - `Authorization: Bearer <PAT>` (без токена API отвечает 401 даже на
каталог публичных репозиториев, проверено)."""

from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import quote

from ..config import settings
from .http import JSONClient, limiter_for


def _seg(value: str) -> str:
    return quote(value, safe="")


class SourceCraftAPIClient(JSONClient):
    def __init__(self, token: str | None):
        super().__init__(
            settings.sourcecraft_api_base_url,
            token,
            limiter_for("sourcecraft_api", settings.sourcecraft_api_rps),
            settings.http_timeout_s,
        )

    def _repo(self, org: str, repo: str) -> str:
        return f"/repos/{_seg(org)}/{_seg(repo)}"

    async def _paginate(self, path: str, key: str, params: dict[str, Any] | None = None,
                        limit: int | None = None, page_size: int = 100) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        async for item in self._iter(path, key, params, page_size):
            items.append(item)
            if limit is not None and len(items) >= limit:
                break
        return items

    async def _iter(self, path: str, key: str, params: dict[str, Any] | None = None,
                    page_size: int = 100) -> AsyncIterator[dict[str, Any]]:
        # Крутим next_page_token, пока он не пропадёт - иначе получим только первую страницу.
        token = None
        while True:
            query = dict(params or {})
            query["page_size"] = str(page_size)
            if token:
                query["page_token"] = token
            data = await self.get_json(path, query)
            for item in data.get(key) or []:
                yield item
            token = data.get("next_page_token")
            if not token:
                break

    # --- каталог и репозитории ---

    def iter_public_repos(self, page_size: int = 100) -> AsyncIterator[dict[str, Any]]:
        """GET /repos - DiscoverRepositories. Сортировка по created_at, чтобы обход не «плыл»
        при изменении рейтинга лайков во время пагинации (так рекомендует описание sort_by)."""
        return self._iter("/repos", "repositories", {"sort_by": "created_at"}, page_size)

    async def get_repo(self, org: str, repo: str) -> dict[str, Any]:
        return await self.get_json(self._repo(org, repo))

    async def get_repo_by_id(self, repo_id: str) -> dict[str, Any]:
        return await self.get_json(f"/repos/id:{_seg(repo_id)}")

    async def list_org_repos(self, org: str, limit: int = 500) -> list[dict[str, Any]]:
        return await self._paginate(f"/orgs/{_seg(org)}/repos", "repositories", limit=limit)

    async def get_user(self) -> dict[str, Any]:
        return await self.get_json("/user")

    # --- данные для категорий ---

    async def list_tree(self, org: str, repo: str, limit: int = 20000) -> list[dict[str, Any]]:
        return await self._paginate(f"{self._repo(org, repo)}/trees", "trees", {"recursive": "true"}, limit=limit)

    async def list_cicd_runs(self, org: str, repo: str, limit: int) -> list[dict[str, Any]]:
        # Сортировки в ListRuns нет; по умолчанию API отдаёт новые прогоны первыми.
        return await self._paginate(f"{self._repo(org, repo)}/cicd/runs", "runs", limit=limit, page_size=min(limit, 100))

    async def list_issues(self, org: str, repo: str, limit: int) -> list[dict[str, Any]]:
        return await self._paginate(f"{self._repo(org, repo)}/issues", "issues", {"sort_by": "-created_at"}, limit=limit)

    async def list_issue_comments(self, org: str, repo: str, issue_slug: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._paginate(
            f"{self._repo(org, repo)}/issues/{_seg(issue_slug)}/comments", "issue_comments",
            {"sort_by": "created_at"}, limit=limit, page_size=limit,
        )

    async def list_pulls(self, org: str, repo: str, limit: int) -> list[dict[str, Any]]:
        return await self._paginate(f"{self._repo(org, repo)}/pulls", "pull_requests", {"sort_by": "-updated_at"}, limit=limit)

    async def list_contributors(self, org: str, repo: str, limit: int = 1000) -> list[dict[str, Any]]:
        # Организаторы (22.09): считать контрибьюторов этим методом - SourceCraft сам склеивает
        # разные email одного человека, если они привязаны к аккаунту.
        return await self._paginate(f"{self._repo(org, repo)}/contributors", "contributors", limit=limit)

    async def list_releases(self, org: str, repo: str, limit: int = 100) -> list[dict[str, Any]]:
        return await self._paginate(f"{self._repo(org, repo)}/releases", "releases", {"sort_by": "-created_at"}, limit=limit)
