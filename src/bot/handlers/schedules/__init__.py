from aiogram import Router
from aiogram.types import BotCommand

from . import (
    callbacks,
    create,
    list,
    taken,
    history,
)


router = Router()
commands = [
    BotCommand(command="schedule", description="Create new medication schedule"),
    BotCommand(command="list", description="Show active medications"),
    BotCommand(command="taken", description="Confirm dose taken"),
    BotCommand(command="history", description="Show medication adherence history"),
]

router.include_routers(
    callbacks.router, create.router, list.router, taken.router, history.router
)


__all__ = ["router", "commands"]
