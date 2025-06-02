from aiogram.utils.i18n import gettext as _

from src.models import Schedule, User
from src.services.schedule_service import ScheduleService
from src.utils.formatting import format_date, format_time

SPACING = "   "


async def format_schedule(
    user: User, schedule: Schedule, service: ScheduleService
) -> str:
    # Base information
    frequency = _(
        "{frequency} time/day", "{frequency} times/day", schedule.doses_per_day
    ).format(frequency=schedule.doses_per_day)

    text = (
        SPACING + _("💊 Drug: {drug_name}").format(drug_name=schedule.drug_name) + "\n"
    )

    # Dose information
    text += SPACING + _("📏 Dose: {dose}").format(dose=schedule.dose) + "\n"
    text += SPACING + _("⏰ Frequency: {frequency}").format(frequency=frequency) + "\n"

    # Convert times to user's timezone
    start_local = user.in_local_time(schedule.start_datetime)
    end_local = (
        user.in_local_time(schedule.end_datetime) if schedule.end_datetime else None
    )
    end_date = format_date(end_local) if end_local else _("ongoing")
    duration = schedule.duration
    if end_local:
        duration = (end_local - start_local).days

    # Duration information
    if not end_local:
        text += _("   📅 Since {date}\n").format(date=format_date(start_local))
    else:
        text += _(
            "   📅 Duration: {days} day\n", "   📅 Duration: {days} days\n", duration
        ).format(days=duration)
        text += _("      {start} → {end}\n").format(
            start=format_date(start_local), end=end_date
        )

    # Get next dose time
    next_dose = await service.get_next_dose_time(user, schedule)
    # Next dose information
    if next_dose:
        next_local = user.in_local_time(next_dose)
        text += _("   ⏳ Next dose: {time}\n").format(time=format_time(next_local))
    else:
        text += _("   ✅ Course completed\n")

    # Additional comments
    if schedule.comment:
        text += _("   📝 Note: {comment}\n").format(comment=schedule.comment)

    return text
