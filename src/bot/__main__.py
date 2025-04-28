import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import settings
from src.database.connector import async_session
from src.services.llm_service import LLMService

from .handlers import commands, schedules
from .middleware.database import DatabaseMiddleware
from .middleware.user import UserMiddleware


def create_bot():
    return Bot(
        token=settings.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_llm_service():
    return LLMService(
        api_key=settings.llm.api_key.get_secret_value(),
        base_url=settings.llm.url.encoded_string() if settings.llm.url else None,
        default_model=settings.llm.default_model,
        timeout=settings.llm.timeout,
    )


def create_dispatcher(**kwargs):
    dp = Dispatcher(**kwargs)

    # Register middleware
    dp.update.middleware(DatabaseMiddleware(async_session))
    dp.update.middleware(UserMiddleware())

    dp.include_router(commands.router)
    dp.include_router(schedules.router)

    return dp


async def set_bot_commands(bot: Bot):
    await bot.set_my_commands(commands=commands.commands + schedules.commands)


async def main():
    try:
        async with create_llm_service() as llm_service:
            bot = create_bot()
            dp = create_dispatcher(llm_service=llm_service)

            await set_bot_commands(bot)
            logging.info("Bot started. Press Ctrl+C to stop")
            await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
