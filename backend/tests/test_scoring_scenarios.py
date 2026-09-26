"""
Контрольные сценарии методики (CHECK.md, раздел C; ТЗ 13.2 п.3). Проверяют не точное число,
а НАПРАВЛЕНИЕ поведения формулы: существенные проблемы заметно снижают Score, исправления
повышают, отсутствие данных не считается дефектом, второстепенное не определяет итог.

Запуск из backend/:  python -m pytest -q
"""

import unittest
from dataclasses import replace

from app.scoring.aggregate import aggregate
from app.scoring.categories.activity import score_activity
from app.scoring.categories.cicd import score_cicd
from app.scoring.categories.code_health import score_code_health
from app.scoring.categories.documentation import score_documentation
from app.scoring.categories.issues import score_issues
from app.scoring.categories.security import score_security
from app.scoring.engine import evaluate
from app.scoring.facts import (
    ActivityFacts,
    CiCdFacts,
    CiRunFact,
    CodeHealthFacts,
    DocumentationFacts,
    IssuesFacts,
    SecurityFacts,
)
from app.scoring.recommendations import AllFacts


def full_docs(**kw) -> DocumentationFacts:
    base = dict(
        is_empty_repo=False, has_readme=True, readme_has_install_section=True, readme_has_build_test_section=True,
        has_license=True, has_contributing=True, has_codeowners=True, has_build_manifest=True, has_tests=True,
        has_directory_structure=True,
    )
    base.update(kw)
    return DocumentationFacts(**base)


def healthy_facts() -> AllFacts:
    """Сценарий 1: здоровый активный проект."""
    return AllFacts(
        security=SecurityFacts(has_ever_scanned=True),
        cicd=CiCdFacts(has_ever_run=True, recent_runs=[CiRunFact("success", float(i)) for i in range(30)]),
        documentation=full_docs(),
        activity=ActivityFacts(days_since_last_commit=1, commits_per_week_last90d=8, active_authors_last90d=5,
                               merged_prs_last90d=15, days_since_last_release=10, commits_last90d=100),
        issues=IssuesFacts(has_ever_had_issues=True, open_issues_count=3, stale_open_issues_count=0,
                           avg_first_response_days=1, median_close_days=2, critical_or_blocker_open_count=0),
        code_health=CodeHealthFacts(clone_succeeded=True, markers_count=5, kloc=50, stale_markers_count=0),
    )


def healthy_categories():
    f = healthy_facts()
    return {
        "security": score_security(f.security),
        "cicd": score_cicd(f.cicd),
        "documentation": score_documentation(f.documentation),
        "activity": score_activity(f.activity),
        "issues": score_issues(f.issues),
        "code_health": score_code_health(f.code_health),
    }


class ScenarioTests(unittest.TestCase):
    def test_1_healthy_active_project_scores_high(self):
        categories = healthy_categories()
        for name, cs in categories.items():
            self.assertEqual(cs.status, "ok", name)
            self.assertGreaterEqual(cs.score, 70, f"{name}: {cs.score}")
        self.assertGreaterEqual(aggregate(categories), 90)

    def test_2_critical_vulnerabilities_hurt_security_only(self):
        healthy = score_security(SecurityFacts(has_ever_scanned=True))
        vulnerable = score_security(SecurityFacts(has_ever_scanned=True, open_critical_count=2))
        self.assertEqual(healthy.score, 100)
        self.assertLessEqual(vulnerable.score, 61)  # пример из ТЗ: 2 критических -> 61/100
        categories = healthy_categories()
        before = aggregate(categories)
        categories["security"] = vulnerable
        after = aggregate(categories)
        self.assertLessEqual(after, before - 5, "существенная проблема должна заметно снижать итог")

    def test_2b_many_low_findings_do_not_outweigh_one_critical(self):
        many_low = score_security(SecurityFacts(has_ever_scanned=True, open_low_count=200))
        one_critical = score_security(SecurityFacts(has_ever_scanned=True, open_critical_count=1))
        self.assertGreaterEqual(many_low.score, 90)
        self.assertGreater(many_low.score, one_critical.score)

    def test_3_no_ci_is_zero_not_no_data(self):
        cs = score_cicd(CiCdFacts(has_ever_run=False))
        self.assertEqual(cs.score, 0)
        self.assertEqual(cs.status, "ok")

    def test_3b_no_ci_does_not_zero_out_total(self):
        categories = healthy_categories()
        categories["cicd"] = score_cicd(CiCdFacts(has_ever_run=False))
        self.assertGreater(aggregate(categories), 50)  # вес CI 15% - итог не обнуляется

    def test_3c_ci_runs_inaccessible(self):
        without_config = score_cicd(CiCdFacts(has_ever_run=False, runs_available=False, has_ci_config=False))
        with_config = score_cicd(CiCdFacts(has_ever_run=False, runs_available=False, has_ci_config=True))
        self.assertEqual((without_config.status, without_config.score), ("ok", 0))
        self.assertEqual(with_config.status, "no_data")

    def test_3d_failing_ci_is_worse_than_green(self):
        green = [CiRunFact("success", float(i)) for i in range(30)]
        failing = [CiRunFact("failed" if i % 2 else "success", float(i)) for i in range(30)]
        self.assertLessEqual(score_cicd(CiCdFacts(True, failing)).score, score_cicd(CiCdFacts(True, green)).score - 25)

    def test_3e_degrading_ci_is_penalized(self):
        # Одинаково 10 падений из 40; в первом случае - это последние 10 прогонов (деградация).
        degrading = [CiRunFact("failed", float(i)) for i in range(10)] + [CiRunFact("success", float(i)) for i in range(10, 40)]
        recovered = ([CiRunFact("success", float(i)) for i in range(10)] + [CiRunFact("failed", float(i)) for i in range(10, 20)]
                     + [CiRunFact("success", float(i)) for i in range(20, 40)])
        self.assertLess(score_cicd(CiCdFacts(True, degrading)).score, score_cicd(CiCdFacts(True, recovered)).score)

    def test_4_stale_but_documented_project(self):
        activity = score_activity(ActivityFacts(days_since_last_commit=300, commits_per_week_last90d=0,
                                                active_authors_last90d=0, merged_prs_last90d=0,
                                                days_since_last_release=None))
        documentation = score_documentation(DocumentationFacts(
            is_empty_repo=False, has_readme=True, readme_has_install_section=True, readme_has_build_test_section=True,
            has_license=True, has_build_manifest=True))
        self.assertLess(activity.score, 30)
        self.assertGreaterEqual(documentation.score, 65)
        categories = healthy_categories()
        categories["activity"] = activity
        total = aggregate(categories)
        self.assertTrue(40 <= total <= 95, total)  # средний итог, не «весь красный»

    def test_5_empty_repo_is_no_data(self):
        cs = score_documentation(DocumentationFacts(is_empty_repo=True))
        self.assertEqual(cs.status, "no_data")
        self.assertIsNone(cs.score)

    def test_6_many_fresh_todos_not_zeroed(self):
        cs = score_code_health(CodeHealthFacts(clone_succeeded=True, markers_count=40, kloc=50, stale_markers_count=0))
        self.assertGreater(cs.score, 40)

    def test_6b_old_todos_are_worse_than_fresh(self):
        fresh = score_code_health(CodeHealthFacts(clone_succeeded=True, markers_count=20, kloc=10))
        old = score_code_health(CodeHealthFacts(clone_succeeded=True, markers_count=20, kloc=10, stale_markers_count=20))
        self.assertLess(old.score, fresh.score)

    def test_6c_docs_only_repo_code_health_no_data(self):
        cs = score_code_health(CodeHealthFacts(clone_succeeded=True, kloc=0))
        self.assertEqual(cs.status, "no_data")

    def test_7_never_had_issues_is_no_data(self):
        cs = score_issues(IssuesFacts(has_ever_had_issues=False))
        self.assertEqual(cs.status, "no_data")
        self.assertIsNone(cs.score)

    def test_7b_issues_inaccessible_is_no_data(self):
        cs = score_issues(IssuesFacts(has_ever_had_issues=False, issues_available=False))
        self.assertEqual(cs.status, "no_data")

    def test_7c_stale_and_blocker_issues_hurt(self):
        good = score_issues(IssuesFacts(True, open_issues_count=10))
        bad = score_issues(IssuesFacts(True, open_issues_count=10, stale_open_issues_count=8, critical_or_blocker_open_count=3))
        self.assertLess(bad.score, good.score - 30)

    def test_8_never_scanned_is_no_data(self):
        cs = score_security(SecurityFacts(has_ever_scanned=False))
        self.assertEqual(cs.status, "no_data")
        self.assertIsNone(cs.score)

    def test_no_data_excluded_and_renormalized(self):
        categories = healthy_categories()
        categories["security"] = score_security(SecurityFacts(has_ever_scanned=False))
        self.assertGreaterEqual(aggregate(categories), 90)  # не падает из-за отсутствия данных

    def test_all_no_data_total_is_none(self):
        categories = {n: score_security(SecurityFacts(False)) for n in ["security", "cicd"]}
        self.assertIsNone(aggregate(categories))

    def test_empty_commits_cannot_inflate_activity(self):
        honest = ActivityFacts(days_since_last_commit=1, commits_per_week_last90d=5, active_authors_last90d=3,
                               merged_prs_last90d=10, days_since_last_release=10)
        spam = replace(honest, commits_per_week_last90d=500)
        self.assertEqual(score_activity(honest).score, score_activity(spam).score)

    def test_fix_increases_score_via_recommendation(self):
        facts = healthy_facts()
        facts.security = SecurityFacts(has_ever_scanned=True, open_critical_count=2)
        facts.documentation = full_docs(has_license=False)
        result = evaluate(facts)
        self.assertEqual(result.recommendations[0].priority, "high")
        self.assertEqual(result.recommendations[0].category, "security")
        self.assertGreater(result.recommendations[0].score_gain, 0)
        categories = {r.category for r in result.recommendations}
        self.assertIn("documentation", categories)

    def test_strengths_and_weaknesses(self):
        facts = healthy_facts()
        facts.cicd = CiCdFacts(has_ever_run=False)
        result = evaluate(facts)
        self.assertTrue(any(s.startswith("Documentation") for s in result.strengths))
        self.assertTrue(any(w.startswith("CI/CD") for w in result.weaknesses))


if __name__ == "__main__":
    unittest.main()
