from ..facts import DocumentationFacts
from ..result import CategoryScore


def score_documentation(facts: DocumentationFacts) -> CategoryScore:
    score = 0
    if facts.has_readme == True:
      score+=20
    if facts.readme_has_key_sections == True:
      score += 15
    if facts.has_license == True:
      score += 20
    if facts.has_contributing == True:
      score +=10
    if facts.has_codeowners == True:
      score += 10
    if facts.has_build_manifest == True:
      score += 15
    if facts.has_directory_structure == True:
      score += 10
    if facts.is_empty_repo == True:
      return CategoryScore(score=None, status='no_data')
    else:
      return CategoryScore(score=score,status='ok')
