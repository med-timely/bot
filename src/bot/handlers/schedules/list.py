from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.schedule_service import ScheduleService

from .formatters import format_schedule
from .keyboards import get_taken_keyboard

router = Router()


@router.message(Command("list"))
async def handle_list(message: Message, session: AsyncSession, user: User):
    service = ScheduleService(session)

    # Get active schedules (ongoing or not yet started)
    active_schedules = await service.get_active_schedules(user.id, with_doses=True)

    if not active_schedules:
        await message.answer(_("ℹ️ You have no active medication schedules."))
        return

    response = [_("💊 <b>Active Medications:</b>\n")]

    for idx, schedule in enumerate(active_schedules, 1):
        schedule_text = await format_schedule(user, schedule, service)
        response.append(f"{idx}. {schedule_text.strip()}")

    await message.answer(
        "\n\n".join(response),
        parse_mode="HTML",
        reply_markup=get_taken_keyboard(active_schedules),
    )
