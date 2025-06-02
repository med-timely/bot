from aiogram.filters import Command
from aiogram.types import Message

from src.models import User
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


@router.message(Command("me"))
async def handle_me(message: Message, user: User):
    await message.answer(
        _(
            "👤 Your Profile:\n"
            "Name: {name}\n"
            "Username: {username}\n"
            "Role: {role}\n"
            "Language: {language}\n"
            "Timezone: {timezone}\n"
            "Privacy: {privacy}"
        ).format(
            name=user.first_name + (f" {user.last_name}" if user.last_name else ""),
            username=f"@{user.username}" if user.username else _("Not set"),
            role=user.role.value,
            language=user.language_code,
            timezone=user.timezone,
            privacy=_("Accepted") if user.privacy_accepted else _("Not Accepted"),
        )
    )
