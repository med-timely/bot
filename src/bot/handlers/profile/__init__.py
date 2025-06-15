from aiogram import Router
from aiogram.types import BotCommand

from src.i18n import i18n

from . import edit_hours, me

router = Router()
router.include_routers(
    edit_hours.router,
    me.router,
)


def get_commands() -> list[BotCommand]:
    _ = i18n.gettext
    return [
        BotCommand(command="me", description=_("Show your profile information")),
    ]


__all__ = ["router", "get_commands"]
