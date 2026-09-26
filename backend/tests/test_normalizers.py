from datetime import datetime, timedelta, timezone

from app.clients.git_client import Commit
from app.normalizers.activity import normalize_activity
from app.normalizers.cicd import normalize_cicd
from app.normalizers.code_health import is_source_path, scan_text
from app.normalizers.documentation import find_ci_config, normalize_documentation, readme_sections
from app.normalizers.issues import normalize_issues
from app.services.repositories import likes_from_api, parse_repo_ref

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


def iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def test_parse_repo_ref():
    assert parse_repo_ref("https://sourcecraft.dev/org/repo") == ("org", "repo")
    assert parse_repo_ref("https://sourcecraft.dev/org/repo/browse/README.md") == ("org", "repo")
    assert parse_repo_ref("https://git.sourcecraft.dev/org/my.repo.git") == ("org", "my.repo")
    assert parse_repo_ref("org/repo") == ("org", "repo")
    assert parse_repo_ref("just-text") is None


def test_likes_sum_reactions():
    data = {"rating": {"reaction_counts": [{"type": "positive_low", "count": "3"}, {"type": "positive_high", "count": "2"}]}}
    assert likes_from_api(data) == 5


def test_cicd_runs_parsed_and_sorted():
    runs = [
        {"slug": "2", "status": "failed", "event_type": "push",
         "dates": {"started_at": iso(1.1), "finished_at": iso(1.0)}},
        {"slug": "3", "status": "success", "event_type": "pr_update",
         "dates": {"started_at": iso(0.2), "finished_at": iso(0.1)}},
    ]
    facts = normalize_cicd(runs, NOW, "https://sc/o/r", True, ".sourcecraft/ci.yaml")
    assert [r.ref for r in facts.recent_runs] == ["3", "2"]
    assert round(facts.recent_runs[0].duration_minutes) == 144
    assert normalize_cicd(None, NOW, "u", False, None).runs_available is False


def test_issues_stale_critical_response_and_close():
    issues = [
        {"slug": "1", "title": "old", "status": {"status_type": "initial"}, "priority": "blocker",
         "created_at": iso(100), "updated_at": iso(60), "author": {"id": "a"}},
        {"slug": "2", "title": "fresh", "status": {"status_type": "in_progress"}, "priority": "normal",
         "created_at": iso(5), "updated_at": iso(1), "author": {"id": "a"}},
        {"slug": "3", "title": "done", "status": {"status_type": "completed"}, "priority": "normal",
         "created_at": iso(20), "updated_at": iso(10), "completed_at": iso(10), "author": {"id": "a"}},
    ]
    comments = {"2": [{"author": {"id": "a"}, "created_at": iso(4)}, {"author": {"id": "b"}, "created_at": iso(3)}]}
    f = normalize_issues(issues, comments, NOW, "https://sc/o/r")
    assert (f.open_issues_count, f.closed_issues_count, f.stale_open_issues_count) == (2, 1, 1)
    assert f.critical_or_blocker_open_count == 1
    assert round(f.avg_first_response_days) == 2  # ответ не автора через 2 дня
    assert round(f.median_close_days) == 10
    assert f.stale_evidence[0].url.endswith("/issues/1")
    assert normalize_issues([], {}, NOW, "u").has_ever_had_issues is False
    assert normalize_issues(None, {}, NOW, "u").issues_available is False


def test_activity_excludes_empty_commits():
    ts = lambda d: int((NOW - timedelta(days=d)).timestamp())  # noqa: E731
    commits = [Commit("a" * 40, ts(1), "x@e", "X", 3), Commit("b" * 40, ts(2), "x@e", "X", 0),
               Commit("c" * 40, ts(3), "y@e", "Y", 1), Commit("d" * 40, ts(120), "y@e", "Y", 1)]
    pulls = [{"status": "merged", "updated_at": iso(10)}, {"status": "merged", "updated_at": iso(200)}, {"status": "open"}]
    f = normalize_activity(commits, ts(1), NOW, "https://sc/o/r", pulls, [], [{"id": 1}])
    assert f.commits_last90d == 2 and f.empty_commits_excluded == 1
    assert f.active_authors_last90d == 2 and f.commits_prev90d == 1
    assert f.merged_prs_last90d == 1 and f.open_prs == 1
    assert f.days_since_last_release is None and f.releases_available
    assert normalize_activity(None, None, NOW, "u", None, None, None).history_available is False


def test_documentation_checklist():
    paths = ["README.md", "LICENSE", "CONTRIBUTING.md", ".sourcecraft/ci.yaml", "src/app.py", "tests/test_app.py",
             "pyproject.toml", ".sourcecraft/CODEOWNERS"]
    readme = "# App\n\n## Установка\n\n```\npip install app\n```\n\n## Тестирование\n\npytest\n"
    f = normalize_documentation(paths, False, readme)
    assert f.has_readme and f.has_license and f.has_contributing and f.has_codeowners
    assert f.readme_has_install_section and f.readme_has_build_test_section
    assert f.has_build_manifest and f.has_tests and f.has_directory_structure
    assert find_ci_config(paths) == ".sourcecraft/ci.yaml"
    assert readme_sections("# Project\nJust a description.") == (False, False)
    assert normalize_documentation(None, False, None).tree_available is False


def test_code_scanning():
    assert is_source_path("src/main.py")
    assert not is_source_path("node_modules/x/index.js")
    assert not is_source_path("dist/app.min.js")
    assert not is_source_path("docs/README.md")
    loc, markers = scan_text("a.py", b"x = 1\n\n# TODO: fix\ny = 2  # FIXME later\nmy_todo = 3\n")
    assert loc == 4
    assert [(m.line, m.kind) for m in markers] == [(3, "TODO"), (4, "FIXME")]
    assert scan_text("b.bin", b"\0\0TODO") == (0, [])
