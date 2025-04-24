from aiogram import Router
from aiogram.types import BotCommand


router = Router()
commands = [
    BotCommand(command="start", description="Start the bot"),
    BotCommand(command="help", description="Show help"),
    BotCommand(command="me", description="Show your profile information"),
]
