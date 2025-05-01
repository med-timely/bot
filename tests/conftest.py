import os
import sys

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Adjust sys.path to include the parent directory of 'src'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


from src.database.connector import Base


@pytest.fixture(scope="session")
def engine():
    engine = create_async_engine(
        os.getenv(
            "TEST__DB__URL",
            "mariadb+asyncmy://medtimely:medtimely@localhost/medtimely_test",
        )
    )
    return engine


@pytest_asyncio.fixture(autouse=True, scope="session")
async def setup_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def session(engine):
    async with AsyncSession(engine) as session:
        yield session


@pytest.fixture
def bot():
    return Bot(token="123:xyz")


@pytest.fixture
def dp():
    return Dispatcher(storage=MemoryStorage())


@pytest.fixture
def user_data():
    return {
        "telegram_id": "12345678",
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe",
        "role": "patient",
        "language_code": "en",
        "timezone": "UTC",
        "privacy_accepted": True,
    }
