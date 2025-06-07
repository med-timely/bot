import logging

from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.i18n import gettext as _

from src.models import User
from src.services.schedule_service import ScheduleService

from .callbacks_data import StopScheduleCallbackData
from .formatters import format_schedule
from .keyboards import get_stop_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("stop"))
async def command_stop(message: types.Message, session: AsyncSession, user: User):
    """
    Handles the /stop command to initiate the schedule stopping process.
    """
    service = ScheduleService(session)

    active_schedules = await service.get_active_schedules(user.id)

    if not active_schedules:
        await message.answer(_("ℹ️ You have no active medication schedules."))
        return

    await message.answer(
        _("Choose a schedule to stop:"),
        reply_markup=get_stop_keyboard(active_schedules),
    )


@router.callback_query(StopScheduleCallbackData.filter())
async def callback_stop_schedule(
    query: types.CallbackQuery,
    callback_data: StopScheduleCallbackData,
    session: AsyncSession,
    user: User,
):
    """
    Handles the callback query to stop a specific schedule.
    """
    service = ScheduleService(session)

    schedule_id = callback_data.schedule_id
    logger.info("Stopping schedule with id: %s", schedule_id)
    try:
        schedule = await service.stop_schedule(user.id, schedule_id)
        if isinstance(query.message, types.Message):
            await query.message.edit_text(
                _("⏹️ Schedule stopped:\n\n")
                + await format_schedule(user, schedule, service)
            )
    except Exception as e:
        logger.error("Failed to stop schedule %s: %s", schedule_id, e)
        await query.answer(
            _("Failed to stop schedule {schedule_id}.").format(schedule_id=schedule_id)
        )
    await query.answer()
