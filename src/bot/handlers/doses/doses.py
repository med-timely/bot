from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BotCommand

router = Router()
commands = [
    BotCommand(command="taken", description="Confirm dose taken"),
]


@router.message(Command("taken"))
async def handle_taken(message: Message):
    """Handle the /taken command to confirm a medication dose was taken."""
    # TODO: confirm dose taken
    await message.answer(
        "Dose of [medication name] recorded at [time]. Great job! Your next dose is scheduled for [next time]."
    )
