"""
Facts — нормализованные входные данные для формул скоринга (README раздел 3.2).

Это единственный контракт, который должен знать слой сбора данных (клиенты + нормализаторы,
Фаза 1): их задача — превратить сырой ответ SourceCraft API / CLI / SCS API в объект Facts.
Функции в scoring/categories/*.py ничего не знают об HTTP, git или swagger — только про Facts.

Поля называются так же, как переменные в формулах README, чтобы код и документация не расходились.
"""

from dataclasses import dataclass, field


@dataclass
class SecurityFacts:
    has_ever_scanned: bool
    open_critical_count: int = 0
    open_high_count: int = 0
    open_medium_count: int = 0
    open_low_count: int = 0
    evidence_defect_group_ids: list[str] = field(default_factory=list)


@dataclass
class CiRunFact:
    status: str  # см. swagger Run.Status: success, failed, canceled, timeout, rejected, ...
    finished_at_days_ago: float | None  # сколько дней назад завершился прогон


@dataclass
class CiCdFacts:
    has_ever_run: bool
    recent_runs: list[CiRunFact] = field(default_factory=list)  # последние до 50, новые первыми


@dataclass
class DocumentationFacts:
    is_empty_repo: bool
    has_readme: bool = False
    readme_has_key_sections: bool = False  # эвристика: install/usage/build секции найдены
    has_license: bool = False
    has_contributing: bool = False
    has_codeowners: bool = False
    has_build_manifest: bool = False
    has_directory_structure: bool = False


@dataclass
class ActivityFacts:
    days_since_last_commit: float
    commits_per_week_last90d: float
    active_authors_last90d: int
    merged_prs_last90d: int
    days_since_last_release: float | None  # None = релизов не было никогда


@dataclass
class IssuesFacts:
    has_ever_had_issues: bool
    open_issues_count: int = 0
    stale_open_issues_count: int = 0  # открыт и не обновлялся >30 дней
    avg_first_response_days: float | None = None
    median_close_days: float | None = None
    critical_or_blocker_open_count: int = 0
    evidence_stale_issue_ids: list[str] = field(default_factory=list)


@dataclass
class CodeHealthFacts:
    clone_succeeded: bool
    markers_count: int = 0  # TODO+FIXME+HACK+XXX
    kloc: float = 0.0
    stale_markers_count: int = 0  # старше 180 дней
    evidence_marker_locations: list[str] = field(default_factory=list)  # "path:line"
