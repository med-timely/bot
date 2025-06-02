import contextlib

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import settings


def create_bot():
    return Bot(
        token=settings.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


@contextlib.asynccontextmanager
async def get_bot():
    bot = create_bot()
    try:
        yield bot
    finally:
        await bot.session.close()
