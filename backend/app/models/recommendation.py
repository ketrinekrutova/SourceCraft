from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RecommendationRow(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"))
    category: Mapped[str]
    problem: Mapped[str]
    why_it_matters: Mapped[str]
    action: Mapped[str]
    priority: Mapped[str]  # high | medium | low
    expected_impact: Mapped[str]
    evidence_json: Mapped[str]  # список ссылок на Finding, сериализовано
