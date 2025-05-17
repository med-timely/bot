from aiogram import Router
from aiogram.types import BotCommand

from . import callbacks, create, history, list, stop, taken

router = Router()
commands = [
    BotCommand(command="schedule", description="Create new medication schedule"),
    BotCommand(command="list", description="Show active medications"),
    BotCommand(command="taken", description="Confirm dose taken"),
    BotCommand(command="history", description="Show medication adherence history"),
    BotCommand(command="stop", description="Stop medication schedule"),
]

router.include_routers(
    callbacks.router,
    create.router,
    list.router,
    taken.router,
    history.router,
    stop.router,
)


__all__ = ["router", "commands"]
