from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class User(Base):
    """Пользователь, вошедший через Я ID. Я ID нужен для защищённого личного кабинета; доступ к
    данным SourceCraft даёт отдельно введённый PAT (ответы организаторов 18.09 и 22.09).
    PAT хранится только в зашифрованном виде (Fernet, ключ из SECRET_KEY)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    yandex_id: Mapped[str] = mapped_column(String(64), unique=True)
    login: Mapped[str | None] = mapped_column(String(255), default=None)
    display_name: Mapped[str | None] = mapped_column(String(255), default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sc_token_encrypted: Mapped[str | None] = mapped_column(Text, default=None)
    sc_user_id: Mapped[str | None] = mapped_column(String(64), default=None)
    sc_username: Mapped[str | None] = mapped_column(String(255), default=None)
    # Организации, репозитории которых показывать в «Моих репозиториях» (JSON-список slug).
    # Эндпоинта «все репозитории пользователя» в выгрузке API нет - организаторы предложили
    # идти через организации (ListOrganizationRepositories) или явный ввод репозитория.
    sc_orgs_json: Mapped[str] = mapped_column(Text, default="[]")
    token_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class UserRepoAccess(Base):
    """Подтверждённый факт: PAT пользователя видит этот репозиторий (API вернул 200).
    Только по этой записи отдаются закрытые данные - ограничение 11.4 ТЗ."""

    __tablename__ = "user_repo_access"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
