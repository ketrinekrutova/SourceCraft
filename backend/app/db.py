from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

# SQLite: обход каталога и воркеры пишут одновременно - ждём блокировку, а не падаем сразу.
_connect_args = {"timeout": 30} if settings.database_url.startswith("sqlite") else {}
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True, connect_args=_connect_args)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session


async def init_db() -> None:
    from .models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"
