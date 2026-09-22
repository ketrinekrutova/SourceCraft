"""
Контрольные сценарии из CHECK.md, раздел C. Проверяют не точное число, а НАПРАВЛЕНИЕ поведения
формулы — это и есть требование ТЗ 13.2 ("логичность поведения методики").

Запуск: python -m unittest discover -s backend/tests -v  (из корня репозитория)

ВРЕМЕННО ПРОПУЩЕНЫ: логика в scoring/categories/*.py и scoring/aggregate.py откачена до
raise NotImplementedError — реализация обсуждается отдельно, а не пишется молча. Снять
skip, когда логика будет согласована и реализована.
"""

import unittest

from app.scoring.facts import (
    SecurityFacts,
    CiCdFacts,
    CiRunFact,
    DocumentationFacts,
    ActivityFacts,
    IssuesFacts,
    CodeHealthFacts,
)
from app.scoring.categories.security import score_security
from app.scoring.categories.cicd import score_cicd
from app.scoring.categories.documentation import score_documentation
from app.scoring.categories.activity import score_activity
from app.scoring.categories.issues import score_issues
from app.scoring.categories.code_health import score_code_health
from app.scoring.aggregate import aggregate


def healthy_categories():
    """Сценарий 1: здоровый активный проект — высокий Score по всем категориям."""
    return {
        "security": score_security(SecurityFacts(has_ever_scanned=True)),
        "cicd": score_cicd(CiCdFacts(has_ever_run=True, recent_runs=[CiRunFact("success", i) for i in range(30)])),
        "documentation": score_documentation(
            DocumentationFacts(
                is_empty_repo=False,
                has_readme=True,
                readme_has_key_sections=True,
                has_license=True,
                has_contributing=True,
                has_codeowners=True,
                has_build_manifest=True,
                has_directory_structure=True,
            )
        ),
        "activity": score_activity(
            ActivityFacts(
                days_since_last_commit=1,
                commits_per_week_last90d=8,
                active_authors_last90d=5,
                merged_prs_last90d=15,
                days_since_last_release=10,
            )
        ),
        "issues": score_issues(
            IssuesFacts(has_ever_had_issues=True, open_issues_count=3, stale_open_issues_count=0,
                        avg_first_response_days=1, median_close_days=2, critical_or_blocker_open_count=0)
        ),
        "code_health": score_code_health(
            CodeHealthFacts(clone_succeeded=True, markers_count=5, kloc=50, stale_markers_count=0)
        ),
    }


@unittest.skip("scoring/* откачено до NotImplementedError — логика ещё не согласована и не реализована")
class ScenarioTests(unittest.TestCase):
    def test_1_healthy_active_project_scores_high(self):
        categories = healthy_categories()
        for name, cs in categories.items():
            self.assertEqual(cs.status, "ok", name)
            self.assertGreaterEqual(cs.score, 70, f"{name}: {cs.score}")
        self.assertGreaterEqual(aggregate(categories), 70)

    def test_2_critical_vulnerabilities_hurt_security_only(self):
        healthy = score_security(SecurityFacts(has_ever_scanned=True))
        vulnerable = score_security(SecurityFacts(has_ever_scanned=True, open_critical_count=2))
        self.assertLess(vulnerable.score, healthy.score)
        self.assertLessEqual(vulnerable.score, 61)  # пример из ТЗ: 2 критических -> 61/100

    def test_3_no_ci_is_zero_not_no_data(self):
        cs = score_cicd(CiCdFacts(has_ever_run=False))
        self.assertEqual(cs.score, 0)
        self.assertEqual(cs.status, "ok")  # осознанно не no_data, см. README 3.1

    def test_3b_no_ci_does_not_zero_out_total(self):
        categories = healthy_categories()
        categories["cicd"] = score_cicd(CiCdFacts(has_ever_run=False))
        total = aggregate(categories)
        self.assertGreater(total, 50)  # вес CI всего 15%, не должен обнулять итог

    def test_4_stale_but_documented_project(self):
        activity = score_activity(
            ActivityFacts(days_since_last_commit=300, commits_per_week_last90d=0,
                          active_authors_last90d=0, merged_prs_last90d=0, days_since_last_release=None)
        )
        documentation = score_documentation(
            DocumentationFacts(is_empty_repo=False, has_readme=True, readme_has_key_sections=True,
                                has_license=True, has_build_manifest=True)
        )
        self.assertLess(activity.score, 30)
        self.assertGreaterEqual(documentation.score, 65)

    def test_5_empty_repo_is_no_data(self):
        cs = score_documentation(DocumentationFacts(is_empty_repo=True))
        self.assertEqual(cs.status, "no_data")
        self.assertIsNone(cs.score)

    def test_6_many_fresh_todos_not_zeroed(self):
        cs = score_code_health(CodeHealthFacts(clone_succeeded=True, markers_count=40, kloc=50, stale_markers_count=0))
        self.assertGreater(cs.score, 40)  # density низкий, но freshness=40 полностью

    def test_7_never_had_issues_is_no_data(self):
        cs = score_issues(IssuesFacts(has_ever_had_issues=False))
        self.assertEqual(cs.status, "no_data")
        self.assertIsNone(cs.score)

    def test_8_never_scanned_is_no_data(self):
        cs = score_security(SecurityFacts(has_ever_scanned=False))
        self.assertEqual(cs.status, "no_data")
        self.assertIsNone(cs.score)

    def test_no_data_excluded_and_renormalized(self):
        categories = healthy_categories()
        categories["security"] = score_security(SecurityFacts(has_ever_scanned=False))
        # security весит 20% — без него сумма весов остальных 80, результат считается относительно них
        total = aggregate(categories)
        self.assertGreaterEqual(total, 70)


if __name__ == "__main__":
    unittest.main()
