from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CategoryScoreRow(Base):
    __tablename__ = "category_scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    category: Mapped[str]  # documentation | cicd | security | activity | issues | code_health
    score: Mapped[int | None]
    status: Mapped[str]  # ok | no_data
    explanation: Mapped[str]
    analyzed_at: Mapped[datetime]
    is_full_pass: Mapped[bool] = mapped_column(default=False)  # см. README: быстрый vs полный обход
