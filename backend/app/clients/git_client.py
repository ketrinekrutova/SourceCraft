"""Работа с git-копией репозитория через git.sourcecraft.dev.

Проверено на реальном сервере SourceCraft:
  * анонимный `git clone` публичных репозиториев работает (API без токена - нет);
  * partial clone (`--filter=blob:none`) сервер НЕ поддерживает («filtering not recognized by
    server») - поэтому ограничиваем объём не фильтром, а глубиной истории: `--shallow-since`.

Почему --shallow-since=<history_days>: всем метрикам нужна история не глубже 180 дней
(активность - 90 дней + тренд, «старые» TODO - старше 180 дней). Строки, которые `git blame`
относит к границе shallow-истории (флаг boundary), гарантированно старше окна - это и есть
«старый» маркер. Так крупный репозиторий с 20 000+ коммитов не тянет всю историю.

Рабочая копия не создаётся (`--no-checkout`): файлы читаются прямо из объектов через
`git cat-file --batch`, а весь каталог удаляется сразу после анализа (ТЗ, ограничение 11.2).
Все команды синхронные - вызываются из потока через asyncio.to_thread."""

import base64
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path


class GitError(Exception):
    def __init__(self, message: str, kind: str = "unavailable"):
        super().__init__(message)
        self.kind = kind  # no_access | not_found | unavailable | timeout


@dataclass
class GitAuth:
    """PAT пользователя для закрытых репозиториев. Передаётся через GIT_CONFIG_* в окружении,
    а не в URL или аргументах командной строки - чтобы токен не светился в списке процессов."""

    token: str
    username: str | None = None

    def header_variants(self) -> list[str]:
        basic = base64.b64encode(f"{self.username or 'oauth2'}:{self.token}".encode()).decode()
        return [f"Authorization: Basic {basic}", f"Authorization: Bearer {self.token}"]


@dataclass
class Commit:
    sha: str
    timestamp: int
    author_email: str
    author_name: str
    files_changed: int


@dataclass
class TreeFile:
    path: str
    oid: str
    size: int
    mode: str


@dataclass
class BlameLine:
    line: int
    author_time: int
    boundary: bool
    sha: str


@dataclass
class ClonedRepo:
    path: Path
    shallow: bool
    head_sha: str = ""
    extra: dict = field(default_factory=dict)


def _run(args: list[str], cwd: Path | None = None, env: dict | None = None, timeout: float = 300,
         input_bytes: bytes | None = None) -> bytes:
    full_env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1", "LC_ALL": "C"}
    if env:
        full_env.update(env)
    try:
        proc = subprocess.run(
            ["git", "-c", "core.longpaths=true", "-c", "core.quotepath=false", *args],
            cwd=cwd, env=full_env, capture_output=True, timeout=timeout, input=input_bytes,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitError(f"git {args[0]}: timeout {timeout}s", "timeout") from exc
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        raise GitError(f"git {args[0]} failed: {stderr[-500:]}", _classify(stderr))
    return proc.stdout


def _classify(stderr: str) -> str:
    low = stderr.lower()
    if "authentication" in low or "403" in low or "401" in low or "could not read username" in low:
        return "no_access"
    if "not found" in low or "404" in low or "does not exist" in low:
        return "not_found"
    return "unavailable"


def _rmtree(path: Path) -> None:
    def on_error(func, p, _exc):  # git-объекты на Windows read-only
        os.chmod(p, stat.S_IWRITE)
        func(p)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=on_error)
    else:
        shutil.rmtree(path, onerror=on_error)


def make_workdir(base: str = "") -> Path:
    return Path(tempfile.mkdtemp(prefix="rh-", dir=base or None))


def remove_workdir(path: Path) -> None:
    if path.exists():
        _rmtree(path)


def clone(clone_url: str, dest: Path, history_days: int, timeout: float, auth: GitAuth | None = None) -> ClonedRepo:
    since = (datetime.now(timezone.utc) - timedelta(days=history_days)).strftime("%Y-%m-%d")
    base_args = ["clone", "--quiet", "--no-checkout", "--single-branch", "--no-tags"]
    header_options = auth.header_variants() if auth else [None]

    last_error: GitError | None = None
    for header in header_options:
        env = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraHeader", "GIT_CONFIG_VALUE_0": header} if header else None
        for depth_args in ([f"--shallow-since={since}"], ["--depth", "1"]):
            remove_workdir(dest)
            try:
                _run([*base_args, *depth_args, clone_url, str(dest)], env=env, timeout=timeout)
            except GitError as exc:
                last_error = exc
                if exc.kind in ("no_access", "not_found", "timeout"):
                    break  # глубина тут ни при чём - пробуем другой способ авторизации
                continue  # «нет коммитов после даты» и т.п. - повторяем с --depth 1
            shallow = _run(["rev-parse", "--is-shallow-repository"], cwd=dest).decode().strip() == "true"
            head = _run(["rev-parse", "HEAD"], cwd=dest).decode().strip()
            return ClonedRepo(path=dest, shallow=shallow, head_sha=head)
    assert last_error is not None
    raise last_error


def ls_remote(url: str, timeout: float = 30) -> bool:
    """Существует ли публичный репозиторий (анонимный доступ по git)."""
    try:
        _run(["ls-remote", "--heads", url], timeout=timeout)
        return True
    except GitError:
        return False


def commits(repo: ClonedRepo, since_days: int) -> list[Commit]:
    """Коммиты без merge-коммитов за since_days дней. files_changed считается по --raw (дерево,
    без содержимого файлов): коммит без изменений файлов - «пустой», его отбрасывает методика."""
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = _run(["log", "--no-merges", f"--since={since}", "--format=%x1e%H%x1f%at%x1f%ae%x1f%an", "--raw", "--no-renames"],
               cwd=repo.path, timeout=300).decode("utf-8", "replace")
    result = []
    for record in out.split("\x1e"):
        if not record.strip():
            continue
        header, _, rest = record.partition("\n")
        parts = header.split("\x1f")
        if len(parts) < 4:
            continue
        files = sum(1 for line in rest.splitlines() if line.startswith(":"))
        result.append(Commit(parts[0], int(parts[1]), parts[2].strip().lower(), parts[3].strip(), files))
    return result


def head_commit_time(repo: ClonedRepo) -> int:
    return int(_run(["log", "-1", "--format=%ct"], cwd=repo.path).decode().strip())


def commit_count(repo: ClonedRepo) -> int:
    return int(_run(["rev-list", "--count", "HEAD"], cwd=repo.path).decode().strip())


def list_files(repo: ClonedRepo) -> list[TreeFile]:
    out = _run(["ls-tree", "-r", "-l", "-z", "HEAD"], cwd=repo.path, timeout=300)
    files = []
    for entry in out.split(b"\0"):
        if not entry:
            continue
        meta, _, path = entry.partition(b"\t")
        mode, otype, oid, size = meta.decode().split()
        if otype != "blob":
            continue
        files.append(TreeFile(path.decode("utf-8", "replace"), oid, int(size) if size != "-" else 0, mode))
    return files


def read_blobs(repo: ClonedRepo, oids: list[str]) -> Iterator[tuple[str, bytes]]:
    """Потоковое чтение содержимого объектов одним процессом `git cat-file --batch`
    (не держит весь репозиторий в памяти)."""
    if not oids:
        return
    fd, list_path = tempfile.mkstemp(prefix="rh-oids-")
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(oids) + "\n")
    try:
        with open(list_path, "rb") as stdin:
            proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=repo.path, stdin=stdin,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            assert proc.stdout is not None
            try:
                while True:
                    header = proc.stdout.readline()
                    if not header:
                        break
                    parts = header.decode().split()
                    if len(parts) < 3 or parts[1] == "missing":
                        continue
                    size = int(parts[2])
                    data = proc.stdout.read(size)
                    proc.stdout.read(1)
                    yield parts[0], data
            finally:
                proc.stdout.close()
                proc.wait(timeout=60)
    finally:
        os.remove(list_path)


def blame(repo: ClonedRepo, path: str, timeout: float = 60) -> list[BlameLine]:
    out = _run(["blame", "--line-porcelain", "HEAD", "--", path], cwd=repo.path, timeout=timeout)
    lines: list[BlameLine] = []
    current: dict = {}
    for raw in out.split(b"\n"):
        if raw.startswith(b"\t"):
            if current:
                lines.append(BlameLine(current["final"], current.get("time", 0), current.get("boundary", False), current["sha"]))
            current = {}
            continue
        text = raw.decode("utf-8", "replace")
        if not current:
            parts = text.split()
            if len(parts) >= 3 and len(parts[0]) == 40:
                current = {"sha": parts[0], "final": int(parts[2])}
            continue
        if text.startswith("author-time "):
            current["time"] = int(text.split()[1])
        elif text == "boundary":
            current["boundary"] = True
    return lines


def file_last_commit_time(repo: ClonedRepo, path: str) -> int | None:
    out = _run(["log", "-1", "--format=%ct", "--", path], cwd=repo.path).decode().strip()
    return int(out) if out else None
