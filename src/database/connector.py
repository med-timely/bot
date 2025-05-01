import contextlib
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_database_url():
    from src.config import settings

    return settings.db.url.encoded_string()


def get_sessionmaker():
    from src.config import settings

    engine = create_async_engine(
        get_database_url(),
        echo=settings.db.echo,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


@contextlib.asynccontextmanager
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
