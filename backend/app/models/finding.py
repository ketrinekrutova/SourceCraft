from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Finding(Base):
    """Сырые факты — источник для evidence в рекомендациях (README 3.3)."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    category: Mapped[str]
    kind: Mapped[str]  # defect_group | ci_run | issue | commit | pull_request | todo_marker
    ref: Mapped[str]  # id/ссылка на объект-источник
    payload_json: Mapped[str]  # сериализованный сырой факт
