"""Сбор фактов по одному репозиторию из всех источников.

Источники независимы: отказ одного превращается в «Нет данных» соответствующей категории
(с понятной причиной), а не в падение всего анализа. Код репозитория не сохраняется - клон
удаляется в finally сразу после разбора (ТЗ, ограничение 11.2)."""

import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from ..clients import git_client as git
from ..clients.http import SourceError
from ..clients.scs_security import ENGINE_TYPES, FIXED_STATUSES, SEVERITIES, SCSSecurityClient
from ..clients.sourcecraft_api import SourceCraftAPIClient
from ..config import settings
from ..normalizers.activity import normalize_activity
from ..normalizers.cicd import normalize_cicd
from ..normalizers.code_health import (
    LARGE_FILE_LINES,
    Marker,
    is_source_path,
    normalize_code_health,
    scan_text,
    stable_order_key,
)
from ..normalizers.common import file_url
from ..normalizers.documentation import find_ci_config, find_readme, normalize_documentation
from ..normalizers.issues import normalize_issues
from ..normalizers.security import defect_evidence, normalize_security
from ..scoring.facts import CodeHealthFacts
from ..scoring.recommendations import AllFacts

log = logging.getLogger(__name__)

ProgressFn = Callable[[str, float], Awaitable[None]]

PUBLIC_SECURITY_REASON = (
    "AppSec SourceCraft доступен только пользователю с правами на репозиторий. Войдите через Я ID, "
    "добавьте свой PAT и запустите личный анализ - публичный рейтинг считается без Security"
)
PUBLIC_NO_ACCESS = "{what} этого репозитория доступны только его участникам - для полной оценки запустите личный анализ со своим PAT"
STALE_MARKER_DAYS = 180


@dataclass
class RepoRef:
    id: str
    org: str
    slug: str
    web_url: str
    clone_url: str
    is_empty: bool


@dataclass
class CollectContext:
    repo: RepoRef
    scope: str  # public | personal
    api_token: str | None  # public: сервисный PAT; personal: PAT пользователя
    user_token: str | None = None  # personal: для AppSec и клона закрытого репозитория
    git_auth: git.GitAuth | None = None
    progress: ProgressFn | None = None


@dataclass
class CollectResult:
    facts: AllFacts
    sources: dict[str, str] = field(default_factory=dict)  # источник -> ok | unauthorized | no_access | not_found | error: …
    last_commit_at: datetime | None = None
    partial: bool = False


def _describe(err: Exception) -> str:
    if isinstance(err, SourceError) and err.status == 401:
        return "unauthorized"
    if isinstance(err, (SourceError, git.GitError)):
        return err.kind if err.kind in ("no_access", "not_found") else f"error: {err}"
    return f"error: {type(err).__name__}: {err}"


async def _safe(coro: Awaitable[Any]) -> tuple[Any, Exception | None]:
    try:
        return await coro, None
    except Exception as exc:  # noqa: BLE001 - любой отказ источника = «нет данных», не падение анализа
        return None, exc


def _reason(ctx: CollectContext, err: Exception | None, what: str) -> str:
    kind = getattr(err, "kind", "unavailable")
    if getattr(err, "status", None) == 401:
        if ctx.scope == "public":
            return f"{what}: SourceCraft API не авторизовал сервис (не задан или отклонён SOURCECRAFT_SERVICE_PAT)"
        return f"{what}: SourceCraft отклонил ваш PAT - обновите токен в «Моих репозиториях»"
    if kind in ("no_access", "not_found"):
        if ctx.scope == "public":
            return PUBLIC_NO_ACCESS.format(what=what)
        return f"{what} недоступны с правами вашего токена"
    return f"Источник временно недоступен ({what.lower()}): {err}"


async def collect(ctx: CollectContext) -> CollectResult:
    now = datetime.now(timezone.utc)
    repo = ctx.repo
    sources: dict[str, str] = {}

    async def progress(stage: str, value: float):
        if ctx.progress:
            await ctx.progress(stage, value)

    await progress("METADATA", 0.05)
    async with SourceCraftAPIClient(ctx.api_token) as api:
        (runs, runs_err), (issues, issues_err), (pulls, pulls_err), (releases, rel_err), (contributors, contr_err) = (
            await asyncio.gather(
                _safe(api.list_cicd_runs(repo.org, repo.slug, settings.ci_runs_max)),
                _safe(api.list_issues(repo.org, repo.slug, settings.issues_max)),
                _safe(api.list_pulls(repo.org, repo.slug, settings.pulls_max)),
                _safe(api.list_releases(repo.org, repo.slug)),
                _safe(api.list_contributors(repo.org, repo.slug)),
            )
        )
        for name, err in (("cicd_runs", runs_err), ("issues", issues_err), ("pulls", pulls_err),
                          ("releases", rel_err), ("contributors", contr_err)):
            sources[name] = "ok" if err is None else _describe(err)

        comments_by_slug: dict[str, list[dict]] = {}
        if issues:
            sample = [i for i in issues if i.get("slug")][: settings.issue_comments_sample]
            results = await asyncio.gather(*(_safe(api.list_issue_comments(repo.org, repo.slug, str(i["slug"])))
                                             for i in sample))
            for issue, (comments, err) in zip(sample, results):
                if err is None:
                    comments_by_slug[str(issue["slug"])] = comments
    await progress("METADATA", 0.25)

    # --- git: клон, дерево, README, история, TODO/FIXME ---
    scan: dict[str, Any] | None = None
    scan_err: Exception | None = None
    if not repo.is_empty:
        await progress("CLONING", 0.3)
        workdir = git.make_workdir(settings.work_dir)
        try:
            started = time.monotonic()
            cloned = await asyncio.to_thread(git.clone, repo.clone_url, workdir / "repo", settings.history_days,
                                             settings.clone_timeout_s, ctx.git_auth)
            await progress("CODE_SCAN", 0.5)
            scan = await asyncio.to_thread(_scan_repository, cloned, repo.web_url, now)
            log.info("scanned %s/%s in %.1fs", repo.org, repo.slug, time.monotonic() - started)
            sources["git"] = "ok"
        except Exception as exc:  # noqa: BLE001
            scan_err = exc
            sources["git"] = _describe(exc)
            log.warning("git scan failed for %s/%s: %s", repo.org, repo.slug, exc)
        finally:
            await asyncio.to_thread(git.remove_workdir, workdir)

    # Если git недоступен - дерево файлов для документации берём из API.
    paths = scan["paths"] if scan else None
    readme_text = scan["readme_text"] if scan else None
    if scan is None and not repo.is_empty:
        async with SourceCraftAPIClient(ctx.api_token) as api:
            tree, tree_err = await _safe(api.list_tree(repo.org, repo.slug))
        sources["tree"] = "ok" if tree_err is None else _describe(tree_err)
        if tree is not None:
            paths = [t["path"] for t in tree if t.get("type") in ("file", "executable", "symlink") and t.get("path")]

    # --- AppSec: только личный анализ по PAT пользователя ---
    await progress("SECURITY_SCAN", 0.8)
    security = await _collect_security(ctx, now, sources)

    await progress("SCORING", 0.9)
    ci_config = find_ci_config(paths) if paths is not None else None
    documentation = normalize_documentation(paths, repo.is_empty, readme_text)
    cicd = normalize_cicd(runs, now, repo.web_url, None if paths is None else ci_config is not None, ci_config,
                          no_data_reason=_reason(ctx, runs_err, "Статусы CI/CD") if runs_err else None)
    issues_facts = normalize_issues(issues, comments_by_slug, now, repo.web_url,
                                    limit_hit=issues is not None and len(issues) >= settings.issues_max,
                                    no_data_reason=_reason(ctx, issues_err, "Issues") if issues_err else None)
    git_reason = None
    if repo.is_empty:
        git_reason = "Репозиторий пуст"
    elif scan_err is not None:
        git_reason = f"Не удалось получить git-историю: {scan_err}"
    activity = normalize_activity(
        scan["commits"] if scan else None, scan["head_ts"] if scan else None, now, repo.web_url,
        pulls if pulls_err is None else None, releases if rel_err is None else None,
        contributors if contr_err is None else None, no_data_reason=git_reason,
    )
    if scan:
        code_health = normalize_code_health(
            scan["markers"], scan["stale_flags"], scan["loc_total"], scan["source_files"], scan["large_files"],
            scan["sampled"], scan["age_method"], lambda p, line: file_url(repo.web_url, p, line),
        )
    else:
        code_health = CodeHealthFacts(clone_succeeded=False, no_data_reason=git_reason)

    partial = any(v.startswith("error") for v in sources.values())
    return CollectResult(
        facts=AllFacts(security=security, cicd=cicd, documentation=documentation, activity=activity,
                       issues=issues_facts, code_health=code_health),
        sources=sources,
        last_commit_at=datetime.fromtimestamp(scan["head_ts"], tz=timezone.utc) if scan and scan["head_ts"] else None,
        partial=partial,
    )


async def _collect_security(ctx: CollectContext, now: datetime, sources: dict[str, str]):
    if ctx.scope != "personal" or not ctx.user_token:
        sources["appsec"] = "skipped: public scope"
        return normalize_security(None, {}, {}, {}, 0, [], [], now, no_data_reason=PUBLIC_SECURITY_REASON)

    git_repo = ctx.repo.id
    async with SCSSecurityClient(ctx.user_token) as appsec:
        try:
            scan = await appsec.latest_finished_scan(git_repo)
        except Exception as exc:  # noqa: BLE001
            sources["appsec"] = _describe(exc)
            kind = getattr(exc, "kind", "unavailable")
            reason = ("AppSec недоступен для этого репозитория: нет прав или безопасность не включена в настройках"
                      if kind in ("no_access", "not_found") else f"AppSec временно недоступен: {exc}")
            return normalize_security(None, {}, {}, {}, 0, [], [], now, no_data_reason=reason)
        if scan is None:
            sources["appsec"] = "ok: no scans"
            return normalize_security(None, {}, {}, {}, 0, [], [], now,
                                      no_data_reason="Для репозитория нет завершённых сканирований AppSec SourceCraft")
        scan_uuid = str(scan.get("uuid"))
        try:
            by_severity: dict[str, int] = {}
            evidence = []
            for sev in SEVERITIES:
                total, groups = await appsec.count_defect_groups(
                    git_repo, scan_uuid, severity=[sev], page_size=10 if sev in ("CRITICAL", "HIGH") else 1)
                by_severity[sev] = total
                if sev in ("CRITICAL", "HIGH"):
                    evidence += [defect_evidence(g, sev, ctx.repo.web_url) for g in groups]
            by_engine: dict[str, int] = {}
            secrets_by_sev: dict[str, int] = defaultdict(int)
            secrets_evidence = []
            for engine in ENGINE_TYPES:
                total, groups = await appsec.count_defect_groups(git_repo, scan_uuid, engine_type=engine,
                                                                 page_size=10 if engine == "SECRETS" else 1)
                by_engine[engine] = total
                if engine == "SECRETS" and total:
                    for sev in SEVERITIES:
                        n, _ = await appsec.count_defect_groups(git_repo, scan_uuid, engine_type="SECRETS", severity=[sev])
                        secrets_by_sev[sev] = n
                    secrets_evidence = [defect_evidence(g, "SECRET", ctx.repo.web_url) for g in groups]
            fixed, _ = await appsec.count_defect_groups(git_repo, scan_uuid, status=FIXED_STATUSES)
        except Exception as exc:  # noqa: BLE001
            sources["appsec"] = _describe(exc)
            return normalize_security(None, {}, {}, {}, 0, [], [], now,
                                      no_data_reason=f"Не удалось получить группы дефектов AppSec: {exc}")
    sources["appsec"] = "ok"
    return normalize_security(scan, by_severity, by_engine, dict(secrets_by_sev), fixed, evidence, secrets_evidence, now)


def _scan_repository(cloned: git.ClonedRepo, web_url: str, now: datetime) -> dict[str, Any]:
    files = git.list_files(cloned)
    paths = [f.path for f in files]
    by_path = {f.path: f for f in files}

    readme_path = find_readme(paths)
    readme_text = None
    if readme_path and by_path[readme_path].size <= 512 * 1024:
        for _oid, data in git.read_blobs(cloned, [by_path[readme_path].oid]):
            readme_text = data.decode("utf-8", "replace")

    # Исходники: детерминированная выборка в пределах бюджета - крупный репозиторий не падает
    # по памяти/времени, а один и тот же репозиторий всегда даёт одинаковую выборку.
    candidates = sorted((f for f in files if is_source_path(f.path) and 0 < f.size <= settings.max_file_bytes),
                        key=lambda f: stable_order_key(f.path))
    selected, budget = [], 0
    for f in candidates:
        if len(selected) >= settings.max_scan_files or budget + f.size > settings.max_scan_bytes:
            break
        selected.append(f)
        budget += f.size
    sampled = len(selected) < len(candidates)

    oid_to_paths: dict[str, list[str]] = defaultdict(list)
    for f in selected:
        oid_to_paths[f.oid].append(f.path)
    loc_total, large_files = 0, 0
    markers: list[Marker] = []
    for oid, data in git.read_blobs(cloned, list(oid_to_paths)):
        for path in oid_to_paths[oid]:
            loc, found = scan_text(path, data)
            loc_total += loc
            large_files += loc > LARGE_FILE_LINES
            markers.extend(found)

    # Возраст маркеров: git blame по файлам с наибольшим числом маркеров (с лимитом), строка
    # старше 180 дней или лежащая на границе shallow-истории - «старая».
    stale_border = (now - timedelta(days=STALE_MARKER_DAYS)).timestamp()
    by_file: dict[str, list[Marker]] = defaultdict(list)
    for m in markers:
        by_file[m.path].append(m)
    stale_flags: dict[tuple[str, int], bool] = {}
    blamed_files = sorted(by_file, key=lambda p: -len(by_file[p]))[: settings.blame_max_files]
    for path in blamed_files:
        try:
            lines = {b.line: b for b in git.blame(cloned, path)}
        except git.GitError:
            continue
        for m in by_file[path]:
            b = lines.get(m.line)
            if b is not None:
                stale_flags[(path, m.line)] = (b.boundary and cloned.shallow) or b.author_time < stale_border
    age_method = "blame"
    rest = [p for p in by_file if p not in set(blamed_files)]
    if rest:
        # Прокси для хвоста: дата последнего коммита, менявшего файл (если файл не менялся в окне
        # shallow-истории - он точно старше 180 дней).
        age_method = "blame + дата изменения файла"
        for path in rest[:200]:
            try:
                ts = git.file_last_commit_time(cloned, path)
            except git.GitError:
                continue
            is_old = ts is None or ts < stale_border
            for m in by_file[path]:
                stale_flags[(path, m.line)] = is_old

    commits = git.commits(cloned, since_days=STALE_MARKER_DAYS)
    return {
        "paths": paths,
        "readme_text": readme_text,
        "markers": markers,
        "stale_flags": stale_flags,
        "loc_total": loc_total,
        "source_files": len(selected),
        "large_files": large_files,
        "sampled": sampled,
        "age_method": age_method,
        "commits": commits,
        "head_ts": git.head_commit_time(cloned),
    }


def repo_ref_from_row(row) -> RepoRef:
    clone_url = row.clone_url or f"{settings.sourcecraft_git_base_url.rstrip('/')}/{row.org_slug}/{row.slug}.git"
    return RepoRef(id=row.id, org=row.org_slug, slug=row.slug, web_url=row.web_url, clone_url=clone_url,
                   is_empty=row.is_empty)

