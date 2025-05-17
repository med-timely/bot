from typing import Callable

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.models import Schedule

from .callbacks_data import DoseCallback, StopScheduleCallbackData


def get_schedules_keyboard(
    schedules: list[Schedule],
    prefix: str,
    callback_factory: Callable[[Schedule], CallbackData],
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for schedule in schedules:
        builder.button(
            text=f"{prefix} {schedule.drug_name} ({schedule.dose})",
            callback_data=callback_factory(schedule).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()


def get_taken_keyboard(schedules: list[Schedule]) -> InlineKeyboardMarkup:
    return get_schedules_keyboard(
        schedules, "✅", lambda s: DoseCallback(schedule_id=s.id)
    )


def get_stop_keyboard(schedules: list[Schedule]) -> InlineKeyboardMarkup:
    return get_schedules_keyboard(
        schedules, "⏹️", lambda s: StopScheduleCallbackData(schedule_id=s.id)
    )
