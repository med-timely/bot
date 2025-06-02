from aiogram import Router
from aiogram.types import BotCommand

from src.i18n import i18n

router = Router()


def get_commands(lang: str) -> list[BotCommand]:
    with i18n.context(), i18n.use_locale(lang):
        _ = i18n.gettext
        return [
            BotCommand(command="start", description=_("Start the bot")),
            BotCommand(command="help", description=_("Show help")),
            BotCommand(command="me", description=_("Show your profile information")),
        ]
