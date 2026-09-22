"""grep/blame через CLI -> CodeHealthFacts."""

from ..scoring.facts import CodeHealthFacts


def normalize_code_health(markers: list[dict], marker_dates: list, kloc: float) -> CodeHealthFacts:
    """
    markers — из SourceCraftCLIClient.grep_markers.
    marker_dates — из SourceCraftCLIClient.blame_line_date, по каждому найденному маркеру.
    stale = дата старше 180 дней (README 3.2).
    """
    raise NotImplementedError
