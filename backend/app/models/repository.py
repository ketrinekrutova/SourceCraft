from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Repository(Base):
    """repo_id = Repository.id из основного SourceCraft API (README 1.1)."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(primary_key=True)
    org_slug: Mapped[str]
    repo_slug: Mapped[str]
    name: Mapped[str]
    web_url: Mapped[str]
    primary_language: Mapped[str | None]
    is_public: Mapped[bool] = mapped_column(default=True)
    is_empty: Mapped[bool] = mapped_column(default=False)
    likes: Mapped[int] = mapped_column(default=0)
    last_activity_at: Mapped[datetime | None]
    # gitRepo для SCS Security API — маппинг с id не подтверждён, см. CHECK.md B3.
    scs_git_repo_id: Mapped[str | None]
