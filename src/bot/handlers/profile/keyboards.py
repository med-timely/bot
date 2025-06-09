from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .callbacks import ProfileCallbackData, ProfileOperation


def get_profile_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=_("✏️ Edit Hours"),
        callback_data=ProfileCallbackData(operation=ProfileOperation.EDIT_HOURS).pack(),
    )
    return builder.as_markup()
