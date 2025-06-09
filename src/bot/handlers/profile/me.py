from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.text_decorations import html_decoration as html

from src.models import User

from .keyboards import get_profile_keyboard

router = Router()


@router.message(Command("me"))
async def handle_me(message: Message, user: User):
    await message.answer(
        f"👤 Your Profile:\n"
        f"Name: {html.quote(user.first_name)}{f' {html.quote(user.last_name)}' if user.last_name else ''}\n"
        f"Username: {f'@{user.username}' if user.username else 'Not set'}\n"
        f"Role: {user.role.value}\n"
        f"Language: {user.language_code}\n"
        f"Timezone: {user.timezone}\n"
        f"Daylight Hours: {user.day_start.strftime('%H:%M')}-{user.day_end.strftime('%H:%M')}\n"
        f"Privacy: {'Accepted' if user.privacy_accepted else 'Not Accepted'}",
        reply_markup=get_profile_keyboard(),
        parse_mode=ParseMode.HTML,
    )
