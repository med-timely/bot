import asyncio
import functools
import logging
from datetime import datetime, timezone

from aiogram.utils.i18n import gettext as _
from celery import shared_task

from src.bot import get_bot
from src.bot.handlers.schedules.keyboards import get_taken_keyboard
from src.database.connector import get_db
from src.i18n import use_locale
from src.models import Schedule
from src.services import ScheduleService

logger = logging.getLogger(__name__)


def sync(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(f(*args, **kwargs))

    return wrapper


@shared_task
@sync
async def send_medication_reminders():
    """Periodic task to check for due reminders"""
    async with get_db() as session:
        now = datetime.now(timezone.utc)

        schedules_svc = ScheduleService(session)
        schedules = await schedules_svc.get_active_schedules(
            None, only_today=True, not_taken=True, with_user=True
        )
        schedules_by_user: dict[int, list[Schedule]] = {}
        for schedule in schedules:
            user_id = schedule.user_id
            if user_id not in schedules_by_user:
                schedules_by_user[user_id] = []
            schedules_by_user[user_id].append(schedule)

        for user_id, schedules in schedules_by_user.items():
            user = schedules[0].user
            local_time = user.in_local_time(now).time()
            if local_time < user.day_start or local_time > user.day_end:
                continue

            send_notification.delay(
                user_id=user_id, schedule_ids=[s.id for s in schedules]
            )


@shared_task(
    autoretry_for=(Exception,), retry_backoff=3, retry_kwargs={"max_retries": 3}
)
@sync
async def send_notification(user_id: int, schedule_ids: list[int]):
    """Send reminder to user about multiple schedules"""
    async with get_db() as session, get_bot() as bot:
        schedule_svc = ScheduleService(session)
        schedules = await schedule_svc.select_schedules(
            user_id, schedule_ids, not_taken=True, with_doses=True, with_user=True
        )
        doses = [await schedule_svc.get_current_dose(s) for s in schedules]

        new_doses = [(s, d) for s, d in zip(schedules, doses) if not d.id]
        if not new_doses:
            return

        user = new_doses[0][0].user

        with use_locale(user.language_code):
            header = _("⏰ Reminder: Time to take your medications:") + "\n"
            message = header
            for schedule, _unused in new_doses:
                message += (
                    "    "
                    + _("- {drug}: {dose}").format(
                        drug=schedule.drug_name, dose=schedule.dose
                    )
                    + "\n"
                )

            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                reply_markup=get_taken_keyboard([s for s, _unused in new_doses]),
            )

        for _unused, dose in new_doses:
            dose.taken_datetime = datetime.now(timezone.utc)
            # Mark as "taken" but unconfirmed until user interacts with the notification
            session.add(dose)
