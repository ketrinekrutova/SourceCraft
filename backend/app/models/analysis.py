from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class Analysis(Base):
    """Результат одного завершённого анализа. Хранится вся история, текущим считается последний
    по finished_at для пары (repo_id, owner_user_id).

    owner_user_id = NULL - публичный анализ (только публичные данные, попадает в рейтинг).
    owner_user_id = <user> - личный анализ по PAT пользователя (в т.ч. AppSec); виден только ему
    и никогда не попадает в публичный рейтинг (ответ организаторов 22.09, п. 5)."""

    __tablename__ = "analyses"
    __table_args__ = (Index("ix_analyses_scope", "repo_id", "owner_user_id", "finished_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=None)
    job_id: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[str] = mapped_column(String(16))  # COMPLETED | PARTIAL
    health_score: Mapped[int | None] = mapped_column(default=None)
    verdict: Mapped[str] = mapped_column(String(255), default="")
    methodology_version: Mapped[str] = mapped_column(String(16))
    # Полный результат (категории, детали, рекомендации) - ровно то, что рендерится на странице
    # и в отчёте, поэтому отчёт воспроизводим без повторного обращения к источникам.
    result_json: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
