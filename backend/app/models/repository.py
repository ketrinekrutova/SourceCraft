from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class Repository(Base):
    """Метаданные репозитория из SourceCraft API. id - Repository.id платформы: его же принимает
    AppSec API как gitRepo (описание параметра gitRepo в спецификации appsec.sourcecraft.tech/openapi)."""

    __tablename__ = "repositories"
    __table_args__ = (Index("ix_repositories_org_slug", "org_slug", "slug", unique=True),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_slug: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    web_url: Mapped[str] = mapped_column(String(1024))
    clone_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    default_branch: Mapped[str | None] = mapped_column(String(255), default=None)
    language: Mapped[str | None] = mapped_column(String(128), default=None, index=True)
    visibility: Mapped[str] = mapped_column(String(32), default="public")  # public | internal | private
    is_empty: Mapped[bool] = mapped_column(default=False)
    likes: Mapped[int] = mapped_column(default=0)
    rating_value: Mapped[float | None] = mapped_column(default=None)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Последний коммит по git-истории - точнее, чем last_updated из API; заполняется анализом.
    last_commit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Репозиторий пропал из каталога / стал закрытым - не показываем в рейтинге.
    in_catalog: Mapped[bool] = mapped_column(default=True)
    catalog_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Денормализованный последний ПУБЛИЧНЫЙ результат - чтобы рейтинг всего каталога строился
    # одним индексированным запросом. Личные анализы сюда никогда не пишутся.
    health_score: Mapped[int | None] = mapped_column(default=None, index=True)
    coverage: Mapped[float | None] = mapped_column(default=None)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    analysis_status: Mapped[str | None] = mapped_column(String(16), default=None)  # статус последней публичной задачи

    @property
    def is_public(self) -> bool:
        return self.visibility == "public"

    @property
    def full_name(self) -> str:
        return f"{self.org_slug}/{self.slug}"

    @property
    def last_activity_at(self) -> datetime | None:
        return self.last_commit_at or self.last_updated_at
