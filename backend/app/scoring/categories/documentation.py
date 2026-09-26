from .._utils import no_data, ok
from ..facts import DocumentationFacts
from ..result import CategoryScore, Component, Evidence

# Чек-лист, сумма = 100. Разбивка «секций README» на запуск и сборку/тесты - прямо по списку
# признаков ТЗ 3.1 («инструкция локального запуска», «описание сборки и тестирования»).
CHECKLIST: list[tuple[str, int, str]] = [
    ("has_readme", 20, "README"),
    ("readme_has_install_section", 8, "Инструкция установки / локального запуска в README"),
    ("readme_has_build_test_section", 7, "Описание сборки и тестирования в README"),
    ("has_license", 20, "LICENSE"),
    ("has_contributing", 10, "CONTRIBUTING"),
    ("has_codeowners", 10, "CODEOWNERS"),
    ("has_build_manifest", 10, "Манифест сборки (package.json, pyproject.toml, go.mod, Makefile…)"),
    ("has_tests", 5, "Каталог или файлы тестов"),
    ("has_directory_structure", 10, "Структура каталогов (не плоский набор файлов)"),
]


def score_documentation(facts: DocumentationFacts) -> CategoryScore:
    """Сумма баллов выполненных пунктов чек-листа CHECKLIST.
    «Нет данных» - только пустой репозиторий или недоступное дерево файлов."""
    if facts.is_empty_repo:
        return no_data("Репозиторий пуст - анализировать нечего")
    if not facts.tree_available:
        return no_data("Не удалось получить дерево файлов репозитория")

    components = [
        Component(label, points if getattr(facts, attr) else 0, points, "есть" if getattr(facts, attr) else "нет")
        for attr, points, label in CHECKLIST
    ]
    score = sum(c.points for c in components)
    missing = [label for (attr, _p, label) in CHECKLIST if not getattr(facts, attr)]
    if not missing:
        explanation = "Все признаки зрелой документации на месте"
    elif not facts.has_readme:
        explanation = "Отсутствует README"
    elif not facts.readme_has_install_section:
        explanation = "В README нет инструкции установки и локального запуска"
    elif not facts.has_license:
        explanation = "Отсутствует файл лицензии"
    else:
        explanation = "Не хватает: " + ", ".join(m.split(" (")[0] for m in missing[:3])

    evidence = []
    if facts.readme_path:
        evidence.append(Evidence("file", facts.readme_path))
    details = {
        "readme_path": facts.readme_path,
        "readme_chars": facts.readme_chars,
        "manifest_files": facts.manifest_files[:10],
        "files_total": facts.files_total,
        "missing": missing,
    }
    return ok(score, explanation, components, evidence, details)
