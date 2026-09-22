"""
Генератор рекомендаций (README 3.3): факты -> приоритизированный список.

ИТОГ ОБСУЖДЕНИЯ (нейронка или код): рекомендации — обычный детерминированный код (шаблоны на
Facts), без LLM. Обязательная часть ТЗ (раздел 3.3) требует проблему/причину/факт/действие/
приоритет/эффект — это полностью закрывается условиями и f-строками. AI-рекомендации — отдельная
фича со звёздочкой (раздел 7 ТЗ), которую мы не делаем; там же прямо написано, что выводы ИИ
"должны оставаться проверяемыми и не подменять фактическую аналитику" — то есть даже если её
когда-нибудь добавим, она не выбирает приоритет и не придумывает действие, максимум пересказывает
уже готовые правила текстом (например, отдельный AI-summary-абзац поверх этого списка). Причины
не брать LLM сейчас: 1) обязательный сценарий полностью закрывается кодом, 2) критерий 13.2 ТЗ
требует воспроизводимости, а LLM-вызов — это ещё одна точка нестабильности (задержка/стоимость/
неодинаковый ответ на одинаковых данных), 3) не усложнять то, что не требует усложнения.

ПОРОГИ НИЖЕ ПРИДУМАНЫ CLAUDE, НЕ ОБСУЖДЕНЫ С КОМАНДОЙ. Оставлены как временное решение по
просьбе (лучше рабочий черновик, чем ничего), но это не согласованная методика — при первой
возможности пройтись отдельно и подтвердить/поменять каждый порог:
  - security: рекомендация при open_critical_count > 0 (совпадает с порогом самой формулы Score)
  - documentation: рекомендация при отсутствии README (bool, порогов нет)
  - cicd: рекомендация при fail_rate > 20% — цифра 20% выбрана произвольно, не обоснована
  - issues: рекомендация при stale_open_issues_count > 0 — то есть любая зависшая задача,
    не проверялось на большом количестве репозиториев, может оказаться слишком чувствительным
  - code_health: рекомендация при stale_markers_count > 0 — так же произвольно, без обоснования
"""

from .facts import CiCdFacts, CodeHealthFacts, DocumentationFacts, IssuesFacts, SecurityFacts
from .result import Evidence, Recommendation

_TERMINAL_OK = {"success"}
_TERMINAL = {"success", "failed", "canceled", "timeout", "rejected"}


def generate_recommendations(
    security: SecurityFacts,
    cicd: CiCdFacts,
    documentation: DocumentationFacts,
    issues: IssuesFacts,
    code_health: CodeHealthFacts,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    if security.has_ever_scanned and security.open_critical_count > 0:
        recs.append(
            Recommendation(
                category="security",
                problem=f"{security.open_critical_count} критических уязвимостей в зависимостях",
                why_it_matters="Критические уязвимости — прямой риск эксплуатации",
                action="Обновить уязвимые пакеты до безопасных версий",
                priority="high",
                expected_impact="Повышает категорию Security и итоговый Score",
                evidence=[Evidence(type="vulnerability", ref=ref) for ref in security.evidence_defect_group_ids],
            )
        )

    if not documentation.is_empty_repo and not documentation.has_readme:
        recs.append(
            Recommendation(
                category="documentation",
                problem="Отсутствует README",
                why_it_matters="Без README новый участник не поймёт назначение и способ запуска проекта",
                action="Добавить README с описанием проекта, инструкцией установки и запуска",
                priority="medium",
                expected_impact="Повышает категорию Documentation",
            )
        )

    if cicd.has_ever_run:
        completed = [r for r in cicd.recent_runs[:50] if r.status in _TERMINAL]
        fail_rate = 1 - (sum(1 for r in completed if r.status in _TERMINAL_OK) / len(completed)) if completed else 0
        if fail_rate > 0.2:
            recs.append(
                Recommendation(
                    category="cicd",
                    problem=f"{round(fail_rate * 100)}% последних прогонов CI завершились неуспешно",
                    why_it_matters="Нестабильный CI снижает доверие к статусу сборки и замедляет разработку",
                    action="Разобрать причины падений последних прогонов и стабилизировать пайплайн",
                    priority="medium",
                    expected_impact="Повышает категорию CI/CD",
                )
            )

    if issues.has_ever_had_issues and issues.stale_open_issues_count > 0:
        recs.append(
            Recommendation(
                category="issues",
                problem=f"{issues.stale_open_issues_count} открытых задач не обновлялись более 30 дней",
                why_it_matters="Зависшие задачи создают ощущение заброшенности проекта",
                action="Разобрать зависшие issues: закрыть неактуальные, назначить исполнителей на остальные",
                priority="low",
                expected_impact="Повышает категорию Issues",
                evidence=[Evidence(type="issue", ref=ref) for ref in issues.evidence_stale_issue_ids],
            )
        )

    if code_health.clone_succeeded and code_health.stale_markers_count > 0:
        recs.append(
            Recommendation(
                category="code_health",
                problem=f"{code_health.stale_markers_count} TODO/FIXME старше 6 месяцев",
                why_it_matters="Старый технический долг обычно означает забытые известные проблемы",
                action="Разобрать старые TODO/FIXME: исправить или завести issue",
                priority="low",
                expected_impact="Повышает категорию Code health",
                evidence=[Evidence(type="file", ref=ref) for ref in code_health.evidence_marker_locations],
            )
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: priority_order[r.priority])
    return recs
