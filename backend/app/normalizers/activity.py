"""raw данные (git log через CLI + contributors/pulls/releases API) -> ActivityFacts."""

from typing import Any

from ..scoring.facts import ActivityFacts


def normalize_activity(
    commits: list[dict[str, Any]],       # из SourceCraftCLIClient.git_log_commits
    contributors_response: dict[str, Any],  # GET /repos/{org}/{repo}/contributors
    pulls_response: dict[str, Any],       # GET /repos/{org}/{repo}/pulls (фильтр status == 'merged')
    releases_response: dict[str, Any],    # GET /repos/{org}/{repo}/releases
) -> ActivityFacts:
    raise NotImplementedError
