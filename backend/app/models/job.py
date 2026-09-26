from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class Job(Base):
    """Очередь задач анализа в БД. Воркеры забирают PENDING-задачи через
    SELECT ... FOR UPDATE SKIP LOCKED (Postgres), поэтому процессов-воркеров может быть сколько
    угодно - горизонтальное масштабирование без отдельного брокера."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), default=None)
    trigger: Mapped[str] = mapped_column(String(16))  # schedule | manual | user
    # Чем меньше, тем раньше: ручные запуски пользователей обгоняют ночной пересчёт каталога.
    priority: Mapped[int] = mapped_column(default=100)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING|IN_PROGRESS|COMPLETED|PARTIAL|FAILED
    stage: Mapped[str | None] = mapped_column(String(32), default=None)
    progress: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    worker_id: Mapped[str | None] = mapped_column(String(128), default=None)
    attempts: Mapped[int] = mapped_column(default=0)
    analysis_id: Mapped[int | None] = mapped_column(default=None)
    error_code: Mapped[str | None] = mapped_column(String(64), default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
