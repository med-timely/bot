from aiogram.filters import Command
from aiogram.types import Message

from src.models import User

from .router import router


@router.message(Command("help"))
async def handle_help(message: Message):
    """
    Handle the /help command.
    Sends a message listing all available commands and their descriptions.
    """
    await message.answer(
        "🆘 Help:\n"
        "/me - Show your profile information\n"
        "/schedule - Create medication schedule\n"
        "/list - Show active medications\n"
        "/taken - Confirm dose taken\n"
        "/history - Show medication adherence history"
    )


@router.message(Command("me"))
async def handle_me(message: Message, user: User):
    await message.answer(
        f"👤 Your Profile:\n"
        f"Name: {user.first_name}{f' {user.last_name}' if user.last_name else ''}\n"
        f"Username: {f'@{user.username}' if user.username else 'Not set'}\n"
        f"Role: {user.role.value}\n"
        f"Language: {user.language_code}\n"
        f"Timezone: {user.timezone}\n"
        f"Privacy: {'Accepted' if user.privacy_accepted else 'Not Accepted'}"
    )
