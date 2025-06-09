from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from aiogram.utils.text_decorations import html_decoration as html

from src.models import User
from src.utils.formatting import format_time

from .keyboards import get_profile_keyboard

router = Router()


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
            "Daylight Hours: {day_start} - {day_end}\n"
            "Privacy: {privacy}"
        ).format(
            name=html.quote(user.first_name)
            + (f" {html.quote(user.last_name)}" if user.last_name else ""),
            username=f"@{user.username}" if user.username else _("Not set"),
            role=user.role.value,
            language=user.language_code,
            timezone=user.timezone,
            day_start=format_time(user.day_start),
            day_end=format_time(user.day_end),
            privacy=_("Accepted") if user.privacy_accepted else _("Not Accepted"),
        ),
        reply_markup=get_profile_keyboard(),
        parse_mode=ParseMode.HTML,
    )
