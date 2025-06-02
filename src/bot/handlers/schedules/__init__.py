from typing import List

from aiogram import Router
from aiogram.types import BotCommand

from src.i18n import i18n

from . import callbacks, create, history, list, stop, taken

router = Router()


def get_commands(lang: str) -> List[BotCommand]:
    with i18n.context(), i18n.use_locale(lang):
        _ = i18n.gettext
        return [
            BotCommand(
                command="schedule", description=_("Create new medication schedule")
            ),
            BotCommand(command="list", description=_("Show active medications")),
            BotCommand(command="taken", description=_("Confirm dose taken")),
            BotCommand(
                command="history", description=_("Show medication adherence history")
            ),
            BotCommand(command="stop", description=_("Stop medication schedule")),
        ]


router.include_routers(
    callbacks.router,
    create.router,
    list.router,
    taken.router,
    history.router,
    stop.router,
)


__all__ = ["router", "get_commands"]
