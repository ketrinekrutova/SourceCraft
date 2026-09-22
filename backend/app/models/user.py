from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    """Личность пользователя после входа через Я ID. sourcecraft_pat хранится для приватного
    конвейера — запросы к SourceCraft API/CLI по чужим репозиториям всегда идут с этим токеном,
    никогда сервисным (README 1.1, ограничение 11.4 ТЗ)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)  # id из Я ID
    sourcecraft_user_slug: Mapped[str | None]  # для гипотезы org=username, см. CHECK.md B2
    display_name: Mapped[str | None]
