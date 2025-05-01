from aiogram import Router
from aiogram.types import BotCommand

from . import (
    callbacks,
    create,
    list,
    taken,
)


router = Router()
commands = [
    BotCommand(command="schedule", description="Create new medication schedule"),
    BotCommand(command="list", description="Show active medications"),
    BotCommand(command="taken", description="Confirm dose taken"),
]

router.include_routers(callbacks.router, create.router, list.router, taken.router)


__all__ = ["router", "commands"]
