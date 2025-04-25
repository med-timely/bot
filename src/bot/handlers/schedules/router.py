from aiogram import Router
from aiogram.types import BotCommand


router = Router()
commands = [
    BotCommand(command="schedule", description="Create new medication schedule"),
    BotCommand(command="list", description="Show active medications"),
]
