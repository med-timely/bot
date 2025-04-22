from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BotCommand

router = Router()
commands = [
    BotCommand(command="schedule", description="Create new medication schedule"),
    BotCommand(command="list", description="Show active medications"),
]


@router.message(Command("schedule"))
async def handle_schedule(message: Message):
    """Handle the /schedule command to set up a new medication schedule."""
    # TODO: create new medication schedule
    await message.answer("Let's set up your medication schedule…")


@router.message(Command("list"))
async def handle_list(message: Message):
    """Handle the /list command to display active medications."""
    # TODO: fetch and show active medications
    await message.answer("Here are your active medications…")
