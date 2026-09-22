"""
Клиент api.sourcecraft.tech. Пути и поля сверены с documents/sourcecraft.swagger (1).json.

Реализация (HTTP-вызовы через httpx) — Фаза 1, после CHECK.md блока B (что реально анонимно,
что требует токен). Сейчас — только сигнатуры и точные пути, чтобы Фаза 2/0 могли разрабатываться
параллельно против фикстур.
"""

from typing import Any


class SourceCraftAPIClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url
        self.token = token  # сервисный PAT (публичный конвейер) или PAT пользователя (приватный)

    async def discover_public_repos(self, page_token: str | None = None, page_size: int = 100) -> dict[str, Any]:
        """GET /repos — DiscoverRepositories. Только публичные репозитории, авторизация не подтверждена (CHECK.md B1)."""
        raise NotImplementedError

    async def get_repo(self, org_slug: str, repo_slug: str) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}"""
        raise NotImplementedError

    async def list_tree(self, org_slug: str, repo_slug: str, recursive: bool = True,
                         path: str = "", page_token: str | None = None) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}/trees — отдаёт только name/path/type, без содержимого файла."""
        raise NotImplementedError

    async def list_cicd_runs(self, org_slug: str, repo_slug: str, page_token: str | None = None) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}/cicd/runs"""
        raise NotImplementedError

    async def list_issues(self, org_slug: str, repo_slug: str, page_token: str | None = None) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}/issues"""
        raise NotImplementedError

    async def list_issue_comments(self, issue_id: str, page_token: str | None = None) -> dict[str, Any]:
        """GET /issues/id:{issue_id}/comments — для времени первого ответа. Дорого по запросам,
        ограничивать последними N задачами (см. документы/Источники_данных_по_категориям.pdf)."""
        raise NotImplementedError

    async def list_contributors(self, org_slug: str, repo_slug: str, page_token: str | None = None) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}/contributors"""
        raise NotImplementedError

    async def list_pulls(self, org_slug: str, repo_slug: str, page_token: str | None = None) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}/pulls"""
        raise NotImplementedError

    async def list_releases(self, org_slug: str, repo_slug: str, page_token: str | None = None) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}/releases"""
        raise NotImplementedError

    async def get_rating(self, org_slug: str, repo_slug: str) -> dict[str, Any]:
        """GET /repos/{org_slug}/{repo_slug}/rating — лайки."""
        raise NotImplementedError

    async def list_org_repos(self, org_slug: str, page_token: str | None = None) -> dict[str, Any]:
        """GET /orgs/{org_slug}/repos — гипотеза для приватного конвейера (личное пространство = org
        со slug=username), не подтверждена. См. CHECK.md B2."""
        raise NotImplementedError

    async def get_user(self) -> dict[str, Any]:
        """GET /user"""
        raise NotImplementedError
