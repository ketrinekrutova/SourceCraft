"""
Полный проход: клонирует репозиторий (shallow), считает Code Health и Activity/Documentation
на основе содержимого файлов и git-истории. Запускается для топа рейтинга по расписанию и
по явному запросу пользователя (публичный "проанализировать" или приватный конвейер).

Рабочая копия удаляется сразу после разбора — ограничение 2 раздела 11 ТЗ.
"""


async def run_full_pass_for_repo(repo_id: str, auth_token: str | None = None) -> None:
    """auth_token передаётся только для приватных репозиториев — токен конкретного пользователя,
    никогда сервисный (README 1.1)."""
    raise NotImplementedError


async def run_full_pass_for_top_n(n: int = 50) -> None:
    raise NotImplementedError
