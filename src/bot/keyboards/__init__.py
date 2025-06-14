from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_cancel_button(callback_data: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=_("❌ Cancel"),
        callback_data=callback_data.pack(),
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=_("❌ Cancel"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
