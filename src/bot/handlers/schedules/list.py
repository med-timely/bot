from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Schedule, User
from src.services.schedule_service import ScheduleService

from .router import router


async def format_schedule(
    user: User, schedule: Schedule, service: ScheduleService
) -> str:
    # Get next dose time
    next_dose = await service.get_next_dose_time(user, schedule)

    # Convert times to user's timezone
    start_local = user.in_local_time(schedule.start_datetime)
    end_local = (
        user.in_local_time(schedule.end_datetime) if schedule.end_datetime else None
    )

    # Base information
    text = (
        f"💊 <b>{schedule.drug_name}</b>\n"
        f"   📏 Dose: {schedule.dose}\n"
        f"   ⏰ Frequency: {schedule.doses_per_day}x/day\n"
    )

    # Duration information
    if schedule.duration:
        text += f"   📅 Duration: {schedule.duration} days\n"
        text += f"      {start_local.strftime('%Y-%m-%d')} → {end_local.strftime('%Y-%m-%d') if end_local else "..."}\n"
    else:
        text += "   📅 Ongoing treatment\n"

    # Next dose information
    if next_dose:
        next_local = user.in_local_time(next_dose)
        text += f"   ⏳ Next dose: {next_local.strftime('%a %H:%M')}\n"
    else:
        text += "   ✅ Course completed\n"

    # Additional comments
    if schedule.comment:
        text += f"   📝 Note: {schedule.comment}\n"

    return text


@router.message(Command("list"))
async def handle_list(message: Message, session: AsyncSession, user: User):
    service = ScheduleService(session)

    # Get active schedules (ongoing or not yet started)
    active_schedules = await service.get_active_schedules(user.id)

    if not active_schedules:
        await message.answer("ℹ️ You have no active medication schedules.")
        return

    response = ["💊 <b>Active Medications:</b>\n"]

    for idx, schedule in enumerate(active_schedules, 1):
        schedule_text = await format_schedule(user, schedule, service)
        response.append(f"{idx}. {schedule_text}")

    await message.answer("\n".join(response), parse_mode="HTML")
