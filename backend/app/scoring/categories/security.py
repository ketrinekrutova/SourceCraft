from .._utils import no_data, ok, plural
from ..facts import SecurityFacts
from ..result import CategoryScore, Component

# Штраф за открытые группы дефектов AppSec. Вклад средних и низких ограничен сверху, чтобы
# сотня мелких находок не перевешивала одну критическую (устойчивость методики, ТЗ 13.2 п.5).
CRITICAL_PENALTY = 20
HIGH_PENALTY = 10
MEDIUM_PENALTY, MEDIUM_CAP = 4, 30
LOW_PENALTY, LOW_CAP = 1, 10


def score_security(facts: SecurityFacts) -> CategoryScore:
    """
    penalty = 20×CRITICAL + 10×HIGH + min(30, 4×MEDIUM) + min(10, 1×LOW)   - только открытые группы
    score   = max(0, 100 − penalty)

    Сканов в истории нет / AppSec недоступен → «Нет данных» (сканирование включает не автор
    репозитория, а настройки платформы; подменять его своим сканированием ТЗ запрещает).
    """
    if not facts.has_ever_scanned:
        return no_data(facts.no_data_reason or "Для репозитория нет завершённых сканирований AppSec SourceCraft")

    crit = CRITICAL_PENALTY * facts.open_critical_count
    high = HIGH_PENALTY * facts.open_high_count
    med = min(MEDIUM_CAP, MEDIUM_PENALTY * facts.open_medium_count)
    low = min(LOW_CAP, LOW_PENALTY * facts.open_low_count)
    score = max(0, 100 - (crit + high + med + low))

    components = [
        Component("Критические уязвимости", -crit, 0, str(facts.open_critical_count)),
        Component("Высокие", -high, 0, str(facts.open_high_count)),
        Component("Средние (штраф не более 30)", -med, 0, str(facts.open_medium_count)),
        Component("Низкие (штраф не более 10)", -low, 0, str(facts.open_low_count)),
    ]
    total_open = facts.open_critical_count + facts.open_high_count + facts.open_medium_count + facts.open_low_count
    if total_open == 0:
        explanation = "Открытых уязвимостей по данным AppSec нет"
    else:
        parts = []
        if facts.open_critical_count:
            parts.append(f"{facts.open_critical_count} {plural(facts.open_critical_count, 'критическая', 'критические', 'критических')}")
        if facts.open_high_count:
            parts.append(f"{facts.open_high_count} {plural(facts.open_high_count, 'высокая', 'высокие', 'высоких')}")
        if facts.open_medium_count:
            parts.append(f"{facts.open_medium_count} {plural(facts.open_medium_count, 'средняя', 'средние', 'средних')}")
        if facts.open_low_count:
            parts.append(f"{facts.open_low_count} {plural(facts.open_low_count, 'низкая', 'низкие', 'низких')}")
        explanation = "Открытые уязвимости: " + ", ".join(parts)

    details = {
        "open_critical": facts.open_critical_count,
        "open_high": facts.open_high_count,
        "open_medium": facts.open_medium_count,
        "open_low": facts.open_low_count,
        "open_by_engine": facts.open_by_engine,
        "fixed": facts.fixed_count,
        "scan_finished_days_ago": facts.scan_finished_days_ago,
    }
    return ok(score, explanation, components, facts.evidence + facts.secrets_evidence, details)
