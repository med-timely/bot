import contextlib

from sqlalchemy import AsyncAdaptedQueuePool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import settings

DATABASE_URL = settings.db.url.encoded_string()

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.db.echo,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,
    max_overflow=10,
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_pre_ping=True,  # Test connections before use
    pool_timeout=30,
    # For MySQL 8+ with asyncmy:
    connect_args={
        "connect_timeout": 10,
        "read_timeout": 30,
    },
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@contextlib.asynccontextmanager
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
