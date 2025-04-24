import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from ..config import settings
from ..database.connector import async_session
from .handlers import commands, doses, schedules
from .middleware.database import DatabaseMiddleware
from .middleware.user import UserMiddleware


def create_bot():
    return Bot(
        token=settings.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher():
    dp = Dispatcher()

    # Register middleware
    dp.update.middleware(DatabaseMiddleware(async_session))
    dp.update.middleware(UserMiddleware())

    dp.include_router(commands.router)
    dp.include_router(schedules.router)
    dp.include_router(doses.router)

    return dp


async def set_bot_commands(bot: Bot):
    await bot.set_my_commands(
        commands=commands.commands + schedules.commands + doses.commands
    )


async def main():
    try:
        bot = create_bot()
        dp = create_dispatcher()

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
