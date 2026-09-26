"""
Facts - нормализованные входные данные для формул скоринга (README, раздел «Методика»).

Единственный контракт между слоем сбора данных (clients + normalizers) и формулами
(scoring/categories). Формулы ничего не знают об HTTP, git или swagger - только про Facts.

Флаги *_available различают «источник не ответил / нет прав» (→ «Нет данных») и
«источник ответил, значение нулевое» (→ вычисленный результат, в т.ч. 0).
"""

from dataclasses import dataclass, field

from .result import Evidence


@dataclass
class SecurityFacts:
    has_ever_scanned: bool
    no_data_reason: str | None = None
    open_critical_count: int = 0
    open_high_count: int = 0
    open_medium_count: int = 0
    open_low_count: int = 0
    open_by_engine: dict[str, int] = field(default_factory=dict)  # SAST / SCA / SECRETS
    secrets_by_severity: dict[str, int] = field(default_factory=dict)  # CRITICAL/HIGH/... среди SECRETS
    fixed_count: int = 0  # RESOLVED_FIXED + RESOLVED_AUTOFIXED - «статус исправления» из ТЗ
    scan_finished_days_ago: float | None = None
    evidence: list[Evidence] = field(default_factory=list)  # критичные/высокие группы дефектов
    secrets_evidence: list[Evidence] = field(default_factory=list)


@dataclass
class CiRunFact:
    status: str  # Run.Status из swagger: success, failed, canceled, timeout, skipped, ...
    finished_at_days_ago: float | None
    duration_minutes: float | None = None
    event_type: str | None = None  # push | pr_update | manual | schedule | ...
    ref: str = ""  # slug прогона
    url: str | None = None


@dataclass
class CiCdFacts:
    has_ever_run: bool
    recent_runs: list[CiRunFact] = field(default_factory=list)  # до 50, новые первыми
    runs_available: bool = True  # False - cicd/runs вернул 401/403/ошибку
    no_data_reason: str | None = None
    has_ci_config: bool | None = None  # .sourcecraft/ci.yaml в дереве; None - дерево недоступно
    ci_config_path: str | None = None


@dataclass
class DocumentationFacts:
    is_empty_repo: bool
    tree_available: bool = True
    has_readme: bool = False
    readme_path: str | None = None
    readme_chars: int = 0
    readme_has_install_section: bool = False  # установка / локальный запуск
    readme_has_build_test_section: bool = False  # сборка / тестирование
    has_license: bool = False
    has_contributing: bool = False
    has_codeowners: bool = False
    has_build_manifest: bool = False
    manifest_files: list[str] = field(default_factory=list)
    has_tests: bool = False
    has_directory_structure: bool = False
    files_total: int = 0


@dataclass
class ActivityFacts:
    history_available: bool = True
    days_since_last_commit: float | None = None
    commits_per_week_last90d: float = 0.0
    active_authors_last90d: int = 0
    merged_prs_last90d: int | None = 0  # None - pulls недоступны
    days_since_last_release: float | None = None  # None - релизов не было
    releases_available: bool = True
    no_data_reason: str | None = None
    # Детализация (в Score не входит, показывается как подтверждающие факты):
    commits_last90d: int = 0
    empty_commits_excluded: int = 0
    commits_prev90d: int = 0
    top_author_share: float | None = None
    contributors_total: int | None = None
    open_prs: int | None = None
    releases_total: int = 0
    last_commit_evidence: Evidence | None = None


@dataclass
class IssuesFacts:
    has_ever_had_issues: bool
    issues_available: bool = True
    no_data_reason: str | None = None
    open_issues_count: int = 0
    closed_issues_count: int = 0
    stale_open_issues_count: int = 0  # открыт и не обновлялся > 30 дней
    avg_first_response_days: float | None = None
    median_close_days: float | None = None
    critical_or_blocker_open_count: int = 0
    created_last90d: int = 0
    closed_last90d: int = 0
    sample_limited: bool = False
    stale_evidence: list[Evidence] = field(default_factory=list)
    critical_evidence: list[Evidence] = field(default_factory=list)


@dataclass
class CodeHealthFacts:
    clone_succeeded: bool
    no_data_reason: str | None = None
    markers_count: int = 0  # TODO + FIXME + HACK + XXX
    markers_by_type: dict[str, int] = field(default_factory=dict)
    kloc: float = 0.0
    stale_markers_count: int = 0  # старше 180 дней по git blame
    source_files: int = 0
    sampled: bool = False  # крупный репозиторий: просканирована детерминированная выборка файлов
    age_method: str = "blame"
    large_files: int = 0  # исходники > 1000 строк - признак накопленного техдолга (деталь)
    evidence: list[Evidence] = field(default_factory=list)  # старые маркеры, "path:line"
