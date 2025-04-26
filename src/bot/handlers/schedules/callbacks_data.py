from aiogram.filters.callback_data import CallbackData


class DoseCallback(CallbackData, prefix="dose"):
    schedule_id: int
