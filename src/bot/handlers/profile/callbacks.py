import enum

from aiogram.filters.callback_data import CallbackData


class ProfileOperation(str, enum.Enum):
    EDIT_HOURS = "edit_hours"
    CANCEL = "cancel"


class ProfileCallbackData(CallbackData, prefix="profile"):
    operation: ProfileOperation
