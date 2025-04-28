from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.models import Schedule

from .callbacks_data import DoseCallback


def get_list_keyboard(schedules: list[Schedule]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for schedule in schedules:
        builder.button(
            text=f"✅ Mark {schedule.drug_name} taken",
            callback_data=DoseCallback(schedule_id=schedule.id).pack(),
        )
    # builder.button(text="🔄 Refresh", callback_data="refresh_list")
    builder.adjust(1)
    return builder.as_markup()


def get_taken_keyboard(schedules: list[Schedule]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for schedule in schedules:
        builder.button(
            text=f"💊 {schedule.drug_name} ({schedule.dose})",
            callback_data=DoseCallback(schedule_id=schedule.id).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()
