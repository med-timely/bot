from aiogram.filters import Command
from aiogram.types import Message

from .router import router


@router.message(Command("list"))
async def handle_list(message: Message):
    """Handle the /list command to display active medications."""
    # TODO: fetch and show active medications
    await message.answer("Here are your active medications…")
