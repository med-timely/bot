import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage

from src.config import settings
from src.database.connector import async_session
from src.i18n import i18n
from src.services.llm_service import LLMService

from .bot import get_bot
from .handlers import commands, error, profile, schedules
from .middleware.database import DatabaseMiddleware
from .middleware.i18n import I18nMiddleware
from .middleware.user import UserMiddleware


def create_redis_storage() -> RedisStorage:
    return RedisStorage.from_url(
        url=settings.redis.url.encoded_string(),
        key_builder=DefaultKeyBuilder(prefix="fsm", separator=":", with_destiny=True),
        connection_kwargs={"decode_responses": False, "health_check_interval": 30},
        state_ttl=settings.redis.fsm_ttl,
        data_ttl=settings.redis.fsm_ttl,
    )


def create_llm_service():
    return LLMService(
        api_key=settings.llm.api_key.get_secret_value(),
        base_url=settings.llm.url.encoded_string() if settings.llm.url else None,
        default_model=settings.llm.default_model,
        timeout=settings.llm.timeout,
    )


def create_dispatcher(**kwargs):
    redis_storage = create_redis_storage()
    dp = Dispatcher(storage=redis_storage, **kwargs)

    # Register middleware
    dp.update.outer_middleware(I18nMiddleware(i18n))
    dp.update.middleware(DatabaseMiddleware(async_session))
    dp.update.middleware(UserMiddleware())

    dp.errors.register(error.Handler)

    dp.include_router(commands.router)
    dp.include_router(schedules.router)
    dp.include_router(profile.router)

    return dp


async def set_bot_commands(bot: Bot):
    for lang in [None, "en", "ru"]:  # Supported languages
        with i18n.context(), i18n.use_locale(lang or "en"):
            commands_list = (
                commands.get_commands()
                + schedules.get_commands()
                + profile.get_commands()
            )
            await bot.set_my_commands(commands=commands_list, language_code=lang)


async def main():
    try:
        async with create_llm_service() as llm_service, get_bot() as bot:
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
