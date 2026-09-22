from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AnalysisRun(Base):
    """Статус/время последнего и текущего запуска анализа (README раздел 6)."""

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    pass_type: Mapped[str]  # fast | full
    status: Mapped[str]  # running | success | failed
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    triggered_by_user_id: Mapped[str | None]  # None для кроновых публичных запусков
    error_message: Mapped[str | None]
