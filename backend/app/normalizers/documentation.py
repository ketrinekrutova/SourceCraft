"""Список путей файлов (git ls-tree или API /trees) + текст README -> DocumentationFacts."""

import re
from pathlib import PurePosixPath

from ..scoring.facts import DocumentationFacts

README_NAMES = ("readme.md", "readme.rst", "readme.txt", "readme", "readme.adoc", "readme.markdown")
LICENSE_RE = re.compile(r"^(license|licence|copying|unlicense)(\.[a-z]+)?$|^license-", re.IGNORECASE)
CONTRIBUTING_RE = re.compile(r"^contributing(\.[a-z]+)?$", re.IGNORECASE)
CODEOWNERS_PATHS = {"codeowners", ".sourcecraft/codeowners", "docs/codeowners", ".github/codeowners", ".gitlab/codeowners"}
MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "pipfile", "go.mod",
    "cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "makefile", "cmakelists.txt",
    "gemfile", "composer.json", "build.sbt", "mix.exs", "pubspec.yaml", "deno.json", "meson.build",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yaml", "justfile", "taskfile.yml",
}
CI_CONFIGS = (".sourcecraft/ci.yaml", ".sourcecraft/ci.yml")
TEST_DIR_RE = re.compile(r"(^|/)(tests?|__tests__|spec|specs|testing)/", re.IGNORECASE)
TEST_FILE_RE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.(py|go)|[^/]+\.(test|spec)\.[jt]sx?|[^/]+Test\.(java|kt))$")

# Эвристика по заголовкам README (markdown `#`, rst-подчёркивания, жирный текст) и командам.
INSTALL_RE = re.compile(
    r"install|установк|getting started|quick ?start|быстрый старт|начало работы|запуск|run(ning)? locally|usage|использован|how to run|setup|настройк",
    re.IGNORECASE,
)
BUILD_TEST_RE = re.compile(r"build|сборк|собрат|test|тест|develop|разработк|contribut", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6}\s+.+|.+\n[=\-~^]{3,}\s*$|\*\*.+\*\*\s*$)", re.MULTILINE)
COMMAND_HINT_RE = re.compile(
    r"(pip install|npm (install|ci|run)|yarn|pnpm|go (run|build|test)|cargo (run|build|test)|make\b|docker(-compose| compose)? (up|run|build)|mvn|gradle|pytest|python -m|uvicorn)",
    re.IGNORECASE,
)


def find_readme(paths: list[str]) -> str | None:
    root = {p.lower(): p for p in paths if "/" not in p}
    for name in README_NAMES:
        if name in root:
            return root[name]
    for p in paths:  # README в docs/ тоже считается, но корневой приоритетнее
        if PurePosixPath(p).name.lower() in README_NAMES and p.count("/") == 1 and p.lower().startswith("docs/"):
            return p
    return None


def find_ci_config(paths: list[str]) -> str | None:
    lower = {p.lower(): p for p in paths}
    for name in CI_CONFIGS:
        if name in lower:
            return lower[name]
    return None


def readme_sections(text: str) -> tuple[bool, bool]:
    headings = "\n".join(m.group(0) for m in HEADING_RE.finditer(text))
    commands = COMMAND_HINT_RE.search(text) is not None
    has_install = bool(INSTALL_RE.search(headings)) or (commands and bool(INSTALL_RE.search(text)))
    has_build_test = bool(BUILD_TEST_RE.search(headings)) or bool(re.search(r"pytest|npm test|go test|cargo test|mvn test|gradle test|make test", text, re.IGNORECASE))
    return has_install, has_build_test


def normalize_documentation(paths: list[str] | None, is_empty: bool, readme_text: str | None) -> DocumentationFacts:
    if is_empty:
        return DocumentationFacts(is_empty_repo=True)
    if paths is None:
        return DocumentationFacts(is_empty_repo=False, tree_available=False)

    names_root = [p for p in paths if "/" not in p]
    readme_path = find_readme(paths)
    has_install = has_build_test = False
    if readme_text:
        has_install, has_build_test = readme_sections(readme_text)

    manifests = [p for p in paths if PurePosixPath(p).name.lower() in MANIFESTS and p.count("/") <= 1]
    top_dirs = {p.split("/", 1)[0] for p in paths if "/" in p and not p.startswith(".")}
    return DocumentationFacts(
        is_empty_repo=False,
        tree_available=True,
        has_readme=readme_path is not None,
        readme_path=readme_path,
        readme_chars=len(readme_text or ""),
        readme_has_install_section=has_install,
        readme_has_build_test_section=has_build_test,
        has_license=any(LICENSE_RE.match(n) for n in names_root),
        has_contributing=any(CONTRIBUTING_RE.match(PurePosixPath(p).name) for p in paths if p.count("/") <= 1),
        has_codeowners=any(p.lower() in CODEOWNERS_PATHS for p in paths),
        has_build_manifest=bool(manifests) or find_ci_config(paths) is not None,
        manifest_files=manifests,
        has_tests=any(TEST_DIR_RE.search(p) or TEST_FILE_RE.search(p) for p in paths),
        has_directory_structure=len(top_dirs) >= 1,
        files_total=len(paths),
    )
