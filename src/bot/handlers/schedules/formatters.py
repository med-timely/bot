from aiogram.utils.i18n import gettext as _

from src.models import Schedule, User
from src.services.schedule_service import ScheduleService


async def format_schedule(
    user: User, schedule: Schedule, service: ScheduleService
) -> str:
    # Base information
    text = _(
        "   💊 Drug: {drug_name}\n"
        "   📏 Dose: {dose}\n"
        "   ⏰ Frequency: {frequency} time/day\n",
        "   💊 Drug: {drug_name}\n"
        "   📏 Dose: {dose}\n"
        "   ⏰ Frequency: {frequency} times/day\n",
        schedule.doses_per_day,
    ).format(
        drug_name=schedule.drug_name,
        dose=schedule.dose,
        frequency=schedule.doses_per_day,
    )

    # Convert times to user's timezone
    start_local = user.in_local_time(schedule.start_datetime)
    end_local = (
        user.in_local_time(schedule.end_datetime) if schedule.end_datetime else None
    )
    end_date = end_local.strftime("%Y-%m-%d") if end_local else _("ongoing")
    duration = schedule.duration
    if end_local:
        duration = (end_local - start_local).days

    # Duration information
    if not end_local:
        text += _("   📅 Since {date}\n").format(date=start_local.strftime("%Y-%m-%d"))
    else:
        text += _(
            "   📅 Duration: {days} day\n", "   📅 Duration: {days} days\n", duration
        ).format(days=duration)
        text += _("      {start} → {end}\n").format(
            start=start_local.strftime("%Y-%m-%d"), end=end_date
        )

    # Get next dose time
    next_dose = await service.get_next_dose_time(user, schedule)
    # Next dose information
    if next_dose:
        next_local = user.in_local_time(next_dose)
        text += _("   ⏳ Next dose: {time}\n").format(
            time=next_local.strftime("%a %H:%M")
        )
    else:
        text += _("   ✅ Course completed\n")

    # Additional comments
    if schedule.comment:
        text += _("   📝 Note: {comment}\n").format(comment=schedule.comment)

    return text
