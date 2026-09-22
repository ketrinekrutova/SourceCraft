"""
Быстрый проход (README, идея из documents/Источники_данных_по_категориям.pdf): без клонирования,
только API. Считает Documentation (по именам файлов), CI/CD, Security, Issues, часть Activity —
4.5 из 6 категорий. Запускается по расписанию для всего публичного каталога.

Важно: если Code Health/полная Activity уже считались полным проходом раньше, быстрый проход
их не затирает в no_data — оставляет прошлый результат с пометкой устаревания (README 3, Фаза 3 п.12).
"""


async def run_fast_pass_for_all_public_repos() -> None:
    raise NotImplementedError


async def run_fast_pass_for_repo(repo_id: str) -> None:
    raise NotImplementedError
