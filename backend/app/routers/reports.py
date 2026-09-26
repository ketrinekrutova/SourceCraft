from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_utils import current_user
from ..db import get_session
from ..models import User
from ..reporting.markdown import render_markdown_report
from ..reporting.pdf import PdfFontMissing, render_pdf_report
from ..services.analysis import latest_analysis
from ._views import api_error, build_detail, ensure_personal_access, ensure_public_view, get_repo_or_404, parse_scope

router = APIRouter(tags=["Reports"])


@router.get("/repositories/{repo_id}/report")
async def download_report(repo_id: str, format: str = "markdown", scope: str = "public",
                          session: AsyncSession = Depends(get_session), user: User | None = Depends(current_user)):
    """Отчёт в Markdown или PDF из последнего завершённого анализа - из тех же данных, что и страница."""
    scope = parse_scope(scope)
    if format not in ("markdown", "md", "pdf"):
        raise api_error(400, "UNSUPPORTED_FORMAT", "Поддерживаются форматы markdown и pdf")
    repo = await get_repo_or_404(session, repo_id)
    if scope == "public":
        await ensure_public_view(repo)
        owner = None
    else:
        owner = (await ensure_personal_access(session, user, repo)).id
    analysis = await latest_analysis(session, repo.id, owner)
    if analysis is None:
        raise api_error(409, "NO_ANALYSIS", "Для репозитория ещё нет завершённого анализа")
    detail = build_detail(repo, scope, analysis, None, None)
    basename = f"{repo.org_slug}-{repo.slug}-health{'-personal' if scope == 'personal' else ''}"
    if format == "pdf":
        try:
            content = render_pdf_report(detail)
        except PdfFontMissing as exc:
            raise api_error(500, "PDF_FONT_MISSING", str(exc)) from exc
        return Response(content, media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="{basename}.pdf"'})
    filename = f"{basename}.md"
    return Response(
        render_markdown_report(detail).encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
