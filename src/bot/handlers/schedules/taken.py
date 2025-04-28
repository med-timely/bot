from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.schedules.keyboards import get_taken_keyboard
from src.models import User
from src.services.schedule_service import ScheduleService

from .router import router


@router.message(Command("taken"))
async def handle_taken_command(message: Message, session: AsyncSession, user: User):
    """Handle /taken command to log medication doses"""
    service = ScheduleService(session)

    # Get active schedules with optimized query
    active_schedules = await service.get_active_schedules(
        user.id, with_doses=True, only_today=True, not_taken=True
    )

    if not active_schedules:
        await message.answer("🎉 No active medications to log now!")
        return

    # Send medication selection keyboard
    await message.answer(
        "💊 Which medication did you take?",
        reply_markup=get_taken_keyboard(active_schedules),
    )
