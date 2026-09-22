"""raw /issues (+ комментарии) -> IssuesFacts."""

from typing import Any

from ..scoring.facts import IssuesFacts


def normalize_issues(issues_response: dict[str, Any], comments_by_issue_id: dict[str, list[dict[str, Any]]]) -> IssuesFacts:
    """
    issues_response — GET /repos/{org}/{repo}/issues. Поля Issue: status.status_type, priority,
    created_at, updated_at, completed_at (см. swagger definitions.Issue/IssueStatus/Priority).
    comments_by_issue_id — для avg_first_response_days, собирать только по последним N issues
    (дорого по количеству запросов).
    """
    raise NotImplementedError
