"""raw /trees JSON (+ содержимое файлов через CLI) -> DocumentationFacts."""

from typing import Any

from ..scoring.facts import DocumentationFacts


def normalize_documentation(tree_response: dict[str, Any], readme_content: str | None) -> DocumentationFacts:
    """
    tree_response — ответ GET /repos/{org}/{repo}/trees?recursive=true (имена/пути, без содержимого).
    readme_content — текст README, прочитанный через CLI (clients/sourcecraft_cli.py:read_file),
    нужен только для readme_has_key_sections (эвристика по заголовкам install/usage/build).
    """
    raise NotImplementedError
