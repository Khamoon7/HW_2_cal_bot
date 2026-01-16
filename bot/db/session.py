from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .base import Base


def make_engine(db_path: str):
    """
    Создаёт асинхронный SQLAlchemy engine для SQLite.

    db_path - путь к файлу базы данных.
    """
    return create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,  # SQL-логи выключены
    )


def make_session_factory(engine):
    """
    Создаёт фабрику асинхронных сессий.

    expire_on_commit=False - объекты остаются доступными
    после commit (удобно для бота).
    """
    return async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def init_db(engine) -> None:
    """
    Инициализирует базу данных: создаёт все таблицы,
    описанные в Base.metadata.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
