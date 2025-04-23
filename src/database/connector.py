import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv(
    "DB__URL", "mariadb+asyncmy://medtimely:medtimely@localhost/medtimely"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB__ECHO", "false").lower() in {"1", "true", "yes"},
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
