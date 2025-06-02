import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.handlers import ErrorHandler
from aiogram.types import User, ErrorEvent
from aiogram.utils.i18n import gettext as _

logger = logging.getLogger(__name__)


class Handler(ErrorHandler):
    async def handle(self):
        logger.exception(
            "Cause unexpected exception %s: %s",
            self.exception_name,
            self.exception_message,
        )
        bot: Bot = self.bot
        if not isinstance(self.event, ErrorEvent):
            return

        event: ErrorEvent = self.event
        if not hasattr(event.update.event, "from_user"):
            return

        user: User = event.update.event.from_user
        try:
            await bot.send_message(
                chat_id=user.id,
                text=_(
                    "An error occurred while processing your message. Please try again later."
                ),
            )
        except TelegramBadRequest as e:
            logger.error("Failed to send error message: %s", e)
