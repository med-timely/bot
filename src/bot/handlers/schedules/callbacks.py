from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.schedule_service import ScheduleService

from .callbacks_data import DoseCallback
from .keyboards import get_list_keyboard
from .router import router


@router.callback_query(DoseCallback.filter())
async def handle_dose_callback(
    callback: CallbackQuery,
    callback_data: DoseCallback,
    session: AsyncSession,
    user: User,
):
    schedule_id = callback_data.schedule_id
    service = ScheduleService(session)

    success, message = await service.log_dose(user.id, schedule_id)

    if success:
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(
                reply_markup=get_list_keyboard(
                    await service.get_active_schedules(user.id, with_doses=True)
                )
            )

    await callback.answer(message, show_alert=not success)
