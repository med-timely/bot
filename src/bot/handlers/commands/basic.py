from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _

from .router import router


@router.message(Command("help"))
async def handle_help(message: Message):
    """
    Handle the /help command.
    Sends a message listing all available commands and their descriptions.
    """
    await message.answer(
        _(
            "🆘 Help:\n"
            "/me - Show your profile information\n"
            "/schedule - Create medication schedule\n"
            "/list - Show active medications\n"
            "/taken - Confirm dose taken\n"
            "/history - Show medication adherence history\n"
            "/stop - Stop medication schedule"
        )
    )
