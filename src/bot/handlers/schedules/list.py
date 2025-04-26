from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.schedule_service import ScheduleService

from .formatters import format_schedule
from .keyboards import get_list_keyboard
from .router import router


@router.message(Command("list"))
async def handle_list(message: Message, session: AsyncSession, user: User):
    service = ScheduleService(session)

    # Get active schedules (ongoing or not yet started)
    active_schedules = await service.get_active_schedules(user.id, with_doses=True)

    if not active_schedules:
        await message.answer("ℹ️ You have no active medication schedules.")
        return

    response = ["💊 <b>Active Medications:</b>\n"]

    for idx, schedule in enumerate(active_schedules, 1):
        schedule_text = await format_schedule(user, schedule, service)
        response.append(f"{idx}. {schedule_text.strip()}")

    await message.answer(
        "\n".join(response),
        parse_mode="HTML",
        reply_markup=get_list_keyboard(active_schedules),
    )
