from ..facts import DocumentationFacts
from ..result import CategoryScore


def score_documentation(facts: DocumentationFacts) -> CategoryScore:
    """
    README 3.2, Документация (15%) — чек-лист, сумма = 100:
      README есть: 20 | README с секциями install/usage/build: 15
      LICENSE: 20 | CONTRIBUTING: 10 | CODEOWNERS: 10
      манифест сборки/тестов: 15 | структура каталогов: 10

    is_empty_repo == True -> status="no_data" (весь репозиторий, не только категория).
    """
    raise NotImplementedError
