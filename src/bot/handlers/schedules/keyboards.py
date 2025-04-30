from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.models import Schedule

from .callbacks_data import DoseCallback


def get_taken_keyboard(schedules: list[Schedule]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for schedule in schedules:
        builder.button(
            text=f"💊 {schedule.drug_name} ({schedule.dose})",
            callback_data=DoseCallback(schedule_id=schedule.id).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()
