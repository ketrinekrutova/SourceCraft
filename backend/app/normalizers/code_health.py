"""Содержимое исходников (из git) + даты строк по git blame -> CodeHealthFacts."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from ..scoring.facts import CodeHealthFacts
from ..scoring.result import Evidence

SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".go", ".rs", ".java", ".kt",
    ".kts", ".scala", ".groovy", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".cs", ".fs", ".swift", ".m",
    ".mm", ".rb", ".php", ".pl", ".pm", ".lua", ".r", ".dart", ".ex", ".exs", ".erl", ".hs", ".clj", ".elm",
    ".sh", ".bash", ".zsh", ".ps1", ".sql", ".proto", ".zig", ".nim", ".jl", ".ml", ".pas", ".tf",
}
# Вендоринг, сгенерированный и собранный код - не техдолг авторов репозитория.
SKIP_DIRS = {
    "node_modules", "vendor", "third_party", "third-party", "thirdparty", "external", "dist", "build", "out",
    "target", "bin", "obj", ".git", "__pycache__", "venv", ".venv", "env", ".tox", "site-packages", "bower_components",
    ".next", ".nuxt", "coverage", "generated", "gen", "migrations", ".idea", ".vscode", "Pods",
}
SKIP_SUFFIXES = (".min.js", ".min.css", ".pb.go", "_pb2.py", ".generated.cs", ".g.dart", ".bundle.js")
MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b")
LARGE_FILE_LINES = 1000


def is_source_path(path: str) -> bool:
    p = PurePosixPath(path)
    if p.suffix.lower() not in SOURCE_EXTENSIONS or path.lower().endswith(SKIP_SUFFIXES):
        return False
    return not any(part in SKIP_DIRS for part in p.parts[:-1])


def stable_order_key(path: str) -> str:
    """Детерминированный порядок для выборки файлов крупного репозитория: один и тот же
    репозиторий всегда даёт одну и ту же выборку (воспроизводимость Score)."""
    return hashlib.sha1(path.encode()).hexdigest()


@dataclass
class Marker:
    path: str
    line: int
    kind: str
    text: str


def scan_text(path: str, data: bytes) -> tuple[int, list[Marker]]:
    """-> (непустых строк, маркеры). Бинарные файлы (есть NUL-байт) пропускаются."""
    if b"\0" in data[:8192]:
        return 0, []
    text = data.decode("utf-8", "replace")
    loc = 0
    markers = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            loc += 1
        match = MARKER_RE.search(line)
        if match:
            markers.append(Marker(path, number, match.group(1), line.strip()[:160]))
    return loc, markers


def normalize_code_health(markers: list[Marker], stale_flags: dict[tuple[str, int], bool], loc_total: int,
                          source_files: int, large_files: int, sampled: bool, age_method: str,
                          file_url) -> CodeHealthFacts:
    """stale_flags[(path, line)] - True, если строка с маркером старше 180 дней."""
    by_type: dict[str, int] = {}
    for m in markers:
        by_type[m.kind] = by_type.get(m.kind, 0) + 1
    stale = [m for m in markers if stale_flags.get((m.path, m.line))]
    return CodeHealthFacts(
        clone_succeeded=True,
        markers_count=len(markers),
        markers_by_type=by_type,
        kloc=loc_total / 1000,
        stale_markers_count=len(stale),
        source_files=source_files,
        sampled=sampled,
        age_method=age_method,
        large_files=large_files,
        evidence=[Evidence("file", f"{m.path}:{m.line} {m.text[:80]}", file_url(m.path, m.line)) for m in stale[:10]],
    )
