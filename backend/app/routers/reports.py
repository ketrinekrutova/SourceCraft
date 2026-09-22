from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..reporting.markdown import render_markdown_report

router = APIRouter(tags=["reports"])


@router.get("/repos/{repo_id}/report", response_class=PlainTextResponse)
async def get_report(repo_id: str, format: str = "markdown"):
    """README 4.5: выгрузка отчёта. Markdown — основной формат, рендерится из тех же данных,
    что и /repos/{repo_id}/analysis (не дублировать логику сборки данных).
    render_markdown_report — см. reporting/markdown.py, готовая функция вызывается отсюда."""
    raise NotImplementedError
