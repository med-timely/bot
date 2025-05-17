from aiogram.filters.callback_data import CallbackData


class DoseCallback(CallbackData, prefix="dose"):
    schedule_id: int


class StopScheduleCallbackData(CallbackData, prefix="stop_schedule"):
    schedule_id: int
