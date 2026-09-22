"""
Обёртка над SourceCraft CLI / git. Реализация — Фаза 1, после проверки авторизации CLI для
приватных репозиториев (CHECK.md A4/B4). Рабочая копия удаляется сразу после разбора —
ограничение 2 раздела 11 ТЗ.
"""

from datetime import datetime
from pathlib import Path


class SourceCraftCLIClient:
    async def shallow_clone(self, clone_url: str, dest: Path, auth_token: str | None = None) -> Path:
        """git clone --filter=blob:none --depth <N> <clone_url> <dest>.
        auth_token нужен для приватных репозиториев — способ передачи в CLI не проверен (CHECK.md A4)."""
        raise NotImplementedError

    def read_file(self, repo_path: Path, relative_path: str) -> str | None:
        """Возвращает содержимое файла (для эвристики README/наличия секций), либо None если не найден."""
        raise NotImplementedError

    def git_log_commits(self, repo_path: Path, since_days: int = 90) -> list[dict]:
        """git log --since=<since_days>d --format=... -> [{sha, author, date}]"""
        raise NotImplementedError

    def grep_markers(self, repo_path: Path, patterns: tuple[str, ...] = ("TODO", "FIXME", "HACK", "XXX")) -> list[dict]:
        """-> [{path, line, marker}]. Сначала grep, потом (по найденным строкам) blame — не наоборот."""
        raise NotImplementedError

    def blame_line_date(self, repo_path: Path, file_path: str, line: int) -> datetime | None:
        """git blame -L <line>,<line> --porcelain <file_path>. Вызывать только для строк из grep_markers,
        с лимитом на число файлов — не гонять по всему репозиторию (documents/Источники_данных_по_категориям.pdf)."""
        raise NotImplementedError

    def count_kloc(self, repo_path: Path) -> float:
        """Подсчёт строк кода (tokei/scc или собственный подсчёт) для нормализации плотности TODO/FIXME."""
        raise NotImplementedError
