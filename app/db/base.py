from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Engine and session factory are created lazily via init_db()
# so settings are fully loaded before the engine is built.
_engine = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    global _engine, _AsyncSessionLocal
    _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    _AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine():
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _AsyncSessionLocal is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _AsyncSessionLocal
