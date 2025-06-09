from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import ProfileCallbackData, ProfileOperation


def get_profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✏️ Edit Hours",
        callback_data=ProfileCallbackData(operation=ProfileOperation.EDIT_HOURS).pack(),
    )
    return builder.as_markup()
