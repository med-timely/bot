import os
import sys

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Adjust sys.path to include the parent directory of 'src'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


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
