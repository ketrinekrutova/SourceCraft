"""
Генератор рекомендаций: факты → приоритизированный список (ТЗ 3.3).

Рекомендации - детерминированные правила на Facts, без LLM: обязательная часть ТЗ требует
проблему / причину / факты / действие / приоритет / эффект, и всё это воспроизводимо
выводится из фактов. Каждое правило:

  1. срабатывает по порогу на Facts (пороги и их обоснование - в README, «Рекомендации»);
  2. ссылается на подтверждающие факты (файл, прогон CI, уязвимость, коммит, issue);
  3. описывает «исправленное» состояние фактов - по нему движок ПЕРЕСЧИТЫВАЕТ категорию и
     итоговый Score, поэтому «ожидаемое влияние» - не выдуманная цифра, а разница двух расчётов
     той же формулой (см. engine.py).

Приоритет задаётся правилом (риск: безопасность и сломанный CI - выше, гигиена репозитория -
ниже), внутри одного приоритета сортировка по ожидаемому приросту Score.
"""

from dataclasses import dataclass, replace
from typing import Any, Callable

from .facts import ActivityFacts, CiCdFacts, CiRunFact, CodeHealthFacts, DocumentationFacts, IssuesFacts, SecurityFacts
from .result import Evidence, Priority


@dataclass
class Rule:
    category: str
    priority: Priority
    problem: str
    why: str
    action: str
    facts: str
    evidence: list[Evidence]
    fixed: Any  # Facts категории после исправления - для расчёта эффекта


@dataclass
class AllFacts:
    security: SecurityFacts
    cicd: CiCdFacts
    documentation: DocumentationFacts
    activity: ActivityFacts
    issues: IssuesFacts
    code_health: CodeHealthFacts


def _security_rules(f: SecurityFacts) -> list[Rule]:
    if not f.has_ever_scanned:
        return []
    rules = []
    secrets = f.open_by_engine.get("SECRETS", 0)
    if secrets:
        s = f.secrets_by_severity
        rules.append(Rule(
            "security", "high", f"В коде найдены секреты ({secrets} по данным AppSec SourceCraft)",
            "Утёкший ключ или пароль даёт прямой доступ к инфраструктуре - его нужно считать скомпрометированным",
            "Отзовите и перевыпустите найденные секреты, удалите их из кода и истории, храните в секретах CI",
            f"Открытых групп дефектов SECRETS: {secrets}", f.secrets_evidence,
            replace(f,
                    open_critical_count=max(0, f.open_critical_count - s.get("CRITICAL", 0)),
                    open_high_count=max(0, f.open_high_count - s.get("HIGH", 0)),
                    open_medium_count=max(0, f.open_medium_count - s.get("MEDIUM", 0)),
                    open_low_count=max(0, f.open_low_count - s.get("LOW", 0))),
        ))
    if f.open_critical_count:
        rules.append(Rule(
            "security", "high", f"Критические уязвимости: {f.open_critical_count} по данным AppSec SourceCraft",
            "Критические уязвимости в коде и зависимостях - прямой риск эксплуатации",
            "Обновите уязвимые зависимости до безопасных версий и исправьте найденные в коде проблемы",
            f"Открытых групп дефектов CRITICAL: {f.open_critical_count}",
            [e for e in f.evidence if "CRITICAL" in e.ref][:10] or f.evidence[:10],
            replace(f, open_critical_count=0),
        ))
    if f.open_high_count:
        rules.append(Rule(
            "security", "high", f"Уязвимости высокой критичности: {f.open_high_count}",
            "Высокие уязвимости часто эксплуатируются вместе с другими - их стоит закрыть в ближайшем релизе",
            "Разберите группы дефектов HIGH в AppSec: исправьте или отметьте ложные срабатывания",
            f"Открытых групп дефектов HIGH: {f.open_high_count}",
            [e for e in f.evidence if "HIGH" in e.ref][:10],
            replace(f, open_high_count=0),
        ))
    if f.open_medium_count >= 3 or f.open_low_count >= 5:
        rules.append(Rule(
            "security", "low", f"Незакрытые уязвимости средней и низкой критичности: {f.open_medium_count + f.open_low_count}",
            "Мелкие находки накапливаются и скрывают действительно важные",
            "Запланируйте разбор находок MEDIUM/LOW: исправление или обоснованное закрытие",
            f"MEDIUM: {f.open_medium_count}, LOW: {f.open_low_count}", [],
            replace(f, open_medium_count=0, open_low_count=0),
        ))
    return rules


def _cicd_rules(f: CiCdFacts) -> list[Rule]:
    rules = []
    healthy_runs = [CiRunFact("success", 0.0, event_type="push") for _ in range(20)]
    no_ci = (not f.runs_available and f.has_ci_config is False) or (f.runs_available and not f.recent_runs)
    if no_ci:
        rules.append(Rule(
            "cicd", "medium", "CI не настроен или не запускается",
            "Без автоматической сборки и тестов ошибки попадают в основную ветку незамеченными",
            "Добавьте .sourcecraft/ci.yaml со сборкой и запуском тестов на push и pull request",
            "В дереве нет .sourcecraft/ci.yaml" if f.has_ci_config is False else "Прогонов CI нет",
            [Evidence("file", ".sourcecraft/ci.yaml (отсутствует)")] if f.has_ci_config is False else [],
            CiCdFacts(has_ever_run=True, recent_runs=healthy_runs, has_ci_config=True),
        ))
        return rules
    if not f.runs_available:
        return rules

    completed = [r for r in f.recent_runs if r.status in ("success", "failed", "timeout")]
    if not completed:
        return rules
    failed = [r for r in completed if r.status != "success"]
    fail_rate = len(failed) / len(completed)
    fixed_runs = [replace(r, status="success") for r in f.recent_runs]
    if fail_rate > 0.2:
        rules.append(Rule(
            "cicd", "high" if fail_rate >= 0.5 else "medium",
            f"{round(fail_rate * 100)}% последних прогонов CI завершились неуспешно",
            "Нестабильный CI снижает доверие к статусу сборки и прячет реальные поломки среди «привычных» падений",
            "Разберите причины падений последних прогонов, почините или изолируйте нестабильные тесты",
            f"Неуспешных прогонов: {len(failed)} из {len(completed)}",
            [Evidence("pipeline", f"Прогон #{r.ref}: {r.status}", r.url) for r in failed[:5]],
            replace(f, recent_runs=fixed_runs),
        ))
    finished = [r.finished_at_days_ago for r in f.recent_runs if r.finished_at_days_ago is not None]
    if finished and min(finished) > 30:
        rules.append(Rule(
            "cicd", "low", f"CI не запускался {round(min(finished))} дней",
            "Давно не запускавшийся пайплайн может оказаться сломанным при первом же изменении",
            "Запустите пайплайн вручную или по расписанию, чтобы убедиться, что сборка проходит",
            f"Последний прогон завершился {round(min(finished))} дней назад", [],
            replace(f, recent_runs=[replace(r, finished_at_days_ago=0.0) for r in f.recent_runs]),
        ))
    return rules


def _documentation_rules(f: DocumentationFacts) -> list[Rule]:
    if f.is_empty_repo or not f.tree_available:
        return []
    rules = []

    def rule(attr: str, priority: Priority, problem: str, why: str, action: str, **fixed_extra):
        if not getattr(f, attr):
            rules.append(Rule("documentation", priority, problem, why, action,
                              f"Файл/раздел не найден в дереве репозитория ({problem.lower()})", [],
                              replace(f, **{attr: True}, **fixed_extra)))

    rule("has_readme", "medium", "Отсутствует README",
         "Без README новый участник и потенциальный пользователь не поймут назначение и способ запуска проекта",
         "Добавьте README: назначение проекта, установка, запуск, сборка и тесты",
         readme_has_install_section=True, readme_has_build_test_section=True)
    if f.has_readme:
        rule("readme_has_install_section", "medium", "В README нет инструкции установки и локального запуска",
             "Проект, который нельзя быстро запустить локально, теряет пользователей и контрибьюторов",
             "Добавьте в README раздел «Установка» / «Запуск» с командами для локального старта")
        rule("readme_has_build_test_section", "low", "В README нет описания сборки и тестирования",
             "Без инструкции по тестам изменения от сторонних разработчиков сложно проверить",
             "Опишите в README, как собрать проект и запустить тесты")
    rule("has_license", "medium", "Отсутствует файл лицензии",
         "Без лицензии использовать и дорабатывать код юридически нельзя - открытый проект фактически закрыт",
         "Добавьте файл LICENSE с выбранной лицензией (например, MIT или Apache-2.0)")
    rule("has_contributing", "low", "Отсутствует CONTRIBUTING",
         "Правила участия снижают порог входа для внешних контрибьюторов",
         "Добавьте CONTRIBUTING.md: как предлагать изменения, стиль кода, как запускать проверки")
    rule("has_codeowners", "low", "Отсутствует CODEOWNERS",
         "Без владельцев кода ревью изменений не назначается автоматически",
         "Добавьте CODEOWNERS с ответственными за основные каталоги")
    rule("has_build_manifest", "low", "Не найден манифест сборки",
         "Воспроизводимая сборка начинается с явного описания зависимостей",
         "Добавьте манифест сборки для вашего стека (pyproject.toml, package.json, go.mod, Makefile…)")
    rule("has_tests", "low", "В репозитории не найдены тесты",
         "Без тестов регрессии обнаруживаются только пользователями",
         "Добавьте каталог tests/ и хотя бы базовые тесты основных сценариев")
    return rules


def _activity_rules(f: ActivityFacts) -> list[Rule]:
    if not f.history_available or f.days_since_last_commit is None:
        return []
    rules = []
    if f.days_since_last_commit > 180:
        rules.append(Rule(
            "activity", "medium", f"Последний коммит был {round(f.days_since_last_commit)} дней назад",
            "Заброшенный проект не получает исправлений безопасности - выбирать его зависимостью рискованно",
            "Если проект поддерживается - обновите зависимости и выпустите релиз; если нет - отметьте в README, что он архивный",
            f"Дата последнего коммита: {round(f.days_since_last_commit)} дней назад",
            [f.last_commit_evidence] if f.last_commit_evidence else [],
            replace(f, days_since_last_commit=7.0, commits_per_week_last90d=max(f.commits_per_week_last90d, 1.0)),
        ))
    if f.commits_last90d >= 5 and f.active_authors_last90d == 1:
        rules.append(Rule(
            "activity", "low", "Все изменения за 90 дней внёс один автор (bus factor = 1)",
            "Проект зависит от одного человека: его уход остановит развитие",
            "Вовлеките второго мейнтейнера: ревью, общие права на релизы, документация процессов",
            f"Коммитов за 90 дней: {f.commits_last90d}, активных авторов: 1", [],
            replace(f, active_authors_last90d=2),
        ))
    if f.releases_available and f.days_since_last_release is None and f.commits_last90d > 0:
        rules.append(Rule(
            "activity", "low", "У проекта нет ни одного релиза",
            "Релизы дают пользователям стабильные точки обновления и changelog",
            "Оформите релиз в SourceCraft с тегом и описанием изменений",
            "Список релизов пуст", [], replace(f, days_since_last_release=0.0),
        ))
    return rules


def _issues_rules(f: IssuesFacts) -> list[Rule]:
    if not f.issues_available or not f.has_ever_had_issues:
        return []
    rules = []
    if f.critical_or_blocker_open_count:
        rules.append(Rule(
            "issues", "high", f"Открытые задачи с приоритетом critical/blocker: {f.critical_or_blocker_open_count}",
            "Блокирующие задачи означают известные серьёзные проблемы, которые не решаются",
            "Назначьте исполнителей на critical/blocker-задачи и закройте их в первую очередь",
            f"Открытых critical/blocker: {f.critical_or_blocker_open_count}", f.critical_evidence[:10],
            replace(f, critical_or_blocker_open_count=0),
        ))
    stale_ratio = f.stale_open_issues_count / f.open_issues_count if f.open_issues_count else 0
    if f.stale_open_issues_count and stale_ratio >= 0.2:
        rules.append(Rule(
            "issues", "medium" if stale_ratio >= 0.5 else "low",
            f"{f.stale_open_issues_count} открытых задач не обновлялись более 30 дней",
            "Зависшие задачи создают ощущение заброшенности и прячут актуальные проблемы",
            "Разберите зависшие issues: закройте неактуальные, назначьте исполнителей на остальные",
            f"Зависших: {f.stale_open_issues_count} из {f.open_issues_count} открытых", f.stale_evidence[:10],
            replace(f, stale_open_issues_count=0),
        ))
    if f.avg_first_response_days is not None and f.avg_first_response_days > 7:
        rules.append(Rule(
            "issues", "low", f"Среднее время первого ответа на задачу - {round(f.avg_first_response_days)} дней",
            "Авторы задач без ответа уходят и перестают сообщать о проблемах",
            "Договоритесь о дежурстве по новым задачам и отвечайте хотя бы подтверждением в течение недели",
            f"Среднее время до первого комментария не автора: {round(f.avg_first_response_days, 1)} дней", [],
            replace(f, avg_first_response_days=1.0),
        ))
    return rules


def _code_health_rules(f: CodeHealthFacts) -> list[Rule]:
    if not f.clone_succeeded or f.kloc <= 0:
        return []
    rules = []
    if f.stale_markers_count:
        rules.append(Rule(
            "code_health", "medium" if f.stale_markers_count >= 10 else "low",
            f"{f.stale_markers_count} TODO/FIXME старше 6 месяцев",
            "Старые TODO/FIXME - забытые известные проблемы, которые никто не планирует решать",
            "Разберите старые маркеры: исправьте или перенесите в issues с ответственным",
            f"Возраст определён по git blame; найдено старых маркеров: {f.stale_markers_count}", f.evidence[:10],
            replace(f, markers_count=f.markers_count - f.stale_markers_count, stale_markers_count=0),
        ))
    per_kloc = f.markers_count / f.kloc
    if per_kloc > 5:
        target = int(f.kloc * 2)
        rules.append(Rule(
            "code_health", "medium", f"Высокая плотность TODO/FIXME: {per_kloc:.1f} на 1000 строк",
            "Много незавершённых мест в коде - признак накопленного технического долга",
            "Выделите время на техдолг: закройте часть маркеров и заведите задачи на остальные",
            f"Маркеров: {f.markers_count} на {f.kloc:.1f} тыс. строк кода", [],
            replace(f, markers_count=min(f.markers_count, target),
                    stale_markers_count=min(f.stale_markers_count, target)),
        ))
    return rules


RULES: dict[str, Callable[[Any], list[Rule]]] = {
    "security": _security_rules,
    "cicd": _cicd_rules,
    "documentation": _documentation_rules,
    "activity": _activity_rules,
    "issues": _issues_rules,
    "code_health": _code_health_rules,
}


def collect_rules(facts: AllFacts) -> list[Rule]:
    rules: list[Rule] = []
    for category, fn in RULES.items():
        rules.extend(fn(getattr(facts, category)))
    return rules
