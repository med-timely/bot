from src.models import Schedule, User
from src.services.schedule_service import ScheduleService


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
        f"   💊 Drug: {schedule.drug_name}\n"
        f"   📏 Dose: {schedule.dose}\n"
        f"   ⏰ Frequency: {schedule.doses_per_day}x/day\n"
    )

    # Duration information
    if schedule.duration:
        end_date = end_local.strftime("%Y-%m-%d") if end_local else "ongoing"
        text += f"   📅 Duration: {schedule.duration} days\n"
        text += f"      {start_local.strftime('%Y-%m-%d')} → {end_date}\n"
    else:
        text += f"   📅 Since {start_local.strftime('%Y-%m-%d')}\n"

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
