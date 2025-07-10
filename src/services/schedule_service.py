import logging
from datetime import datetime, time, timedelta, timezone
from typing import Optional

import pytz
from aiogram.utils.i18n import gettext as _
from sqlalchemy import BooleanClauseList, asc, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from src.models import Dose, Schedule, User

logger = logging.getLogger(__name__)


class ScheduleService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # region Create
    async def create_schedule(self, user_id: int, **data) -> Schedule:
        self._validate_schedule_data(data)

        fields = {k: v for k, v in data.items() if k in Schedule.__table__.columns}
        if "start_datetime" not in fields:
            fields["start_datetime"] = datetime.now(timezone.utc)

        schedule = Schedule(user_id=user_id, doses=[], **fields)
        if "end_datetime" not in fields and fields.get("duration"):
            schedule.end_datetime = fields["start_datetime"] + timedelta(
                days=fields["duration"]
            )

        self.session.add(schedule)
        await self.session.commit()

        return schedule

    def _validate_schedule_data(self, data):
        required = ["drug_name", "dose", "doses_per_day"]
        missing = [field for field in required if not data.get(field)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if data["doses_per_day"] < 1:
            raise ValueError("Frequency must be positive number")

        if "duration" in data and data["duration"] is not None and data["duration"] < 1:
            raise ValueError("Duration must be a positive number or not specified")

    # endregion

    # region Read
    async def get_active_schedules(
        self,
        user_id: int | None,
        *,
        with_doses: bool = False,
        with_user: bool = False,
        only_today: bool = False,
        not_taken: bool = False,
    ) -> list[Schedule]:
        """Get active schedules with optimized filters"""
        now = datetime.now(timezone.utc)

        whereclause = self._get_active_filter(now, only_today, not_taken)
        if user_id is not None:
            whereclause &= Schedule.user_id == user_id

        stmt = (
            select(Schedule)
            .join(Schedule.user)
            .options(*self._get_loading_options(with_doses, with_user))
            .where(whereclause)
            .order_by(Schedule.start_datetime)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def select_schedules(
        self,
        user_id: int,
        schedule_ids: list[int],
        *,
        with_doses: bool = False,
        with_user: bool = False,
        only_today: bool = False,
        not_taken: bool = False,
    ) -> list[Schedule]:
        now = datetime.now(timezone.utc)

        whereclause = (
            (Schedule.user_id == user_id)
            & (Schedule.id.in_(schedule_ids))
            & self._get_active_filter(now, only_today, not_taken)
        )

        stmt = (
            select(Schedule)
            .join(Schedule.user)
            .options(
                *self._get_loading_options(with_doses, with_user),
            )
            .where(whereclause)
            .order_by(Schedule.start_datetime)
        )

        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def get_schedule(
        self,
        user_id: int,
        schedule_id: int,
        *,
        with_doses: bool = False,
        only_today: bool = False,
        not_taken: bool = False,
    ) -> Schedule | None:
        schedules = await self.select_schedules(
            user_id,
            [schedule_id],
            with_doses=with_doses,
            only_today=only_today,
            not_taken=not_taken,
        )
        return schedules[0] if schedules else None

    def _get_loading_options(
        self, with_doses: bool, with_user: bool
    ) -> list[ExecutableOption]:
        options = []
        if with_doses:
            options.append(selectinload(Schedule.doses))
        if with_user:
            options.append(selectinload(Schedule.user))
        return options

    def _get_active_filter(
        self, now: datetime, only_today: bool, not_taken: bool = False
    ) -> BooleanClauseList:
        base_filter = (Schedule.end_datetime > now) | (Schedule.end_datetime.is_(None))

        if only_today:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            base_filter = base_filter & (Schedule.start_datetime < today_end)

        if not_taken:
            base_filter = (
                base_filter
                & ~select(1)
                .where(
                    Dose.schedule_id == Schedule.id,
                    Dose.confirmed,
                    Dose.taken_datetime
                    > text(
                        "IF("
                        "`schedules`.`doses_per_day` = 1, "
                        "UTC_DATE(), "
                        "UTC_TIMESTAMP() - INTERVAL ((HOUR(`users`.`day_end`) - HOUR(`users`.`day_start`)) / (`schedules`.`doses_per_day` - 1) / 2) HOUR"
                        ")"
                    ),
                )
                .exists()
            )

        return base_filter

    # endregion

    # region Update
    async def stop_schedule(self, user_id: int, schedule_id: int) -> Schedule:
        """Stops a schedule by setting its end_datetime to now."""
        schedule = await self.get_schedule(user_id, schedule_id)
        if not schedule:
            raise ValueError(
                f"Schedule with id {schedule_id} not found or doesn't belong to user {user_id}"
            )

        if schedule.end_datetime and datetime.now(timezone.utc) > schedule.end_datetime:
            raise ValueError(f"Schedule with id {schedule_id} is already stopped.")

        schedule.end_datetime = datetime.now(timezone.utc)
        await self.session.commit()

        return schedule

    # endregion

    # region Doses
    def get_doses_times(self, user: User, schedule: Schedule) -> list[time]:
        """
        Calculates the times of the doses for the given schedule and user.

        For a one-dose-per-day schedule, returns a list with the user's day start time.
        For a two-dose-per-day schedule, returns a list with the user's day start and day end times.
        For any other number of doses, the times are evenly spaced between the user's day start and day end times.

        :param user: The user for which to calculate the dose times.
        :param schedule: The schedule for which to calculate the dose times.
        :return: A list of times, one for each dose in the schedule.
        """
        if schedule.doses_per_day == 1:
            return [user.day_start]

        if schedule.doses_per_day == 2:
            return [user.day_start, user.day_end]

        interval = user.daylight_duration / (schedule.doses_per_day - 1)
        # Convert start time to minutes for accurate calculation
        start_minutes = user.day_start.hour * 60 + user.day_start.minute

        return [
            time(
                hour=int((start_minutes + i * interval * 60) // 60) % 24,
                minute=int((start_minutes + i * interval * 60) % 60),
            )
            for i in range(0, schedule.doses_per_day)
        ]

    async def get_next_dose_time(
        self, user: User, schedule: Schedule, now_utc: Optional[datetime] = None
    ) -> Optional[datetime]:
        now_utc = now_utc or datetime.now(timezone.utc)
        logger.debug(
            "Calculating next dose time for user %s, schedule %s at %s",
            user.id,
            schedule.id,
            now_utc,
        )

        # Check if schedule has ended
        if schedule.end_datetime is not None and now_utc > schedule.end_datetime:
            logger.debug("Schedule %s has ended", schedule.id)
            return None

        if now_utc < schedule.start_datetime:
            logger.debug(
                "Current time is before schedule start. Adjusting to start time."
            )
            return await self.get_next_dose_time(
                user,
                schedule,
                user.tz.localize(
                    datetime.combine(
                        user.in_local_time(schedule.start_datetime).date(),
                        user.day_start,
                    )
                ).astimezone(timezone.utc),
            )

        # Convert to user's local time for accurate comparison
        local_now = user.in_local_time(now_utc)
        if local_now.time() > user.day_end:
            logger.debug("Current time is after user's day end. Adjusting to next day.")
            return await self.get_next_dose_time(
                user,
                schedule,
                user.tz.localize(
                    datetime.combine(
                        (local_now + timedelta(days=1)).date(),
                        user.day_start,
                    )
                ).astimezone(timezone.utc),
            )

        # Get all taken doses for today, sorted by time
        doses = [
            d
            for d in schedule.doses
            if d.confirmed
            and user.in_local_time(d.taken_datetime).date()
            == user.in_local_time(now_utc).date()
        ]
        logger.debug("Taken doses today: %s", len(doses))

        if len(doses) >= schedule.doses_per_day:
            logger.debug("Maximum doses for today reached. Adjusting to next day.")
            return await self.get_next_dose_time(
                user,
                schedule,
                user.tz.localize(
                    datetime.combine(
                        (local_now + timedelta(days=1)).date(),
                        user.day_start,
                    )
                ).astimezone(timezone.utc),
            )

        doses_times = self.get_doses_times(user, schedule)
        nearest_time = next((t for t in doses_times if t >= local_now.time()), None)

        if nearest_time is None:
            logger.debug("No dose time available for today. Adjusting to next day.")
            return await self.get_next_dose_time(
                user,
                schedule,
                user.tz.localize(
                    datetime.combine(
                        (local_now + timedelta(days=1)).date(),
                        user.day_start,
                    )
                ).astimezone(timezone.utc),
            )

        # Use user's local date for accurate dose time calculation
        next_dose_local = user.tz.localize(
            datetime.combine(local_now.date(), nearest_time)
        )
        logger.debug(
            "Calculated next dose time: %s (local: %s)",
            next_dose_local.astimezone(timezone.utc),
            next_dose_local,
        )

        return max(next_dose_local.astimezone(timezone.utc), now_utc)

    async def get_current_dose(self, user: User, schedule: Schedule) -> Dose:
        now = datetime.now(timezone.utc)
        local_now = user.in_local_time(now)
        local_today = local_now.date()

        # Create proper timezone-aware datetime for the user's local day boundaries
        day_start_local = user.tz.localize(datetime.combine(local_today, time(0, 0, 0)))
        day_start_utc = day_start_local.astimezone(timezone.utc)
        day_end_utc = day_start_utc + timedelta(days=1)

        today_doses = (
            (
                await self.session.execute(
                    select(Dose)
                    .where(
                        (Dose.schedule_id == schedule.id)
                        & (Dose.taken_datetime >= day_start_utc)
                        & (Dose.taken_datetime < day_end_utc)
                    )
                    .order_by(Dose.taken_datetime.desc())
                )
            )
            .scalars()
            .all()
        )

        confirmed_doses = [d for d in today_doses if d.confirmed]

        if len(confirmed_doses) >= schedule.doses_per_day:
            return confirmed_doses[0]

        # if len(confirmed_doses) == 0:
        #     return (
        #         today_doses[0]
        #         if today_doses
        #         else Dose(
        #             user_id=schedule.user_id,
        #             schedule_id=schedule.id,
        #             taken_datetime=now,
        #             confirmed=False,
        #         )
        #     )

        if schedule.doses_per_day == 1:
            return (
                today_doses[0]
                if today_doses
                else Dose(
                    user_id=schedule.user_id,
                    schedule_id=schedule.id,
                    taken_datetime=now,
                    confirmed=False,
                )
            )

        interval_minutes = (user.daylight_duration * 60) / (schedule.doses_per_day - 1)
        doses_times = self.get_doses_times(user, schedule)
        nearest_time = min(
            doses_times,
            key=lambda t: abs(
                (t.hour * 60 + t.minute)
                - (local_now.time().hour * 60 + local_now.time().minute)
            ),
        )
        # Localize with user's timezone, then convert to UTC for comparison
        local_nearest = user.tz.localize(
            datetime.combine(local_today, nearest_time)
        ) - timedelta(minutes=interval_minutes / 2)
        nearest_date = local_nearest.astimezone(timezone.utc)

        nearest_dose = next(
            (d for d in today_doses if d.taken_datetime > nearest_date), None
        )

        if not nearest_dose:
            return Dose(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                taken_datetime=now,
                confirmed=False,
            )

        return nearest_dose

    async def log_dose(self, user_id: int, schedule_id: int) -> tuple[bool, str]:
        """Log a dose taken for a specific schedule

        Args:
            user_id: The user taking the dose
            schedule_id: The schedule ID the dose belongs to

        Returns:
            Tuple of (success, message)
        """

        # Get the schedule and verify it belongs to the user
        stmt = (
            select(Schedule)
            .where(Schedule.id == schedule_id, Schedule.user_id == user_id)
            .options(selectinload(Schedule.user))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            return False, _("Schedule not found or doesn't belong to you")

        if schedule.end_datetime and datetime.now(timezone.utc) > schedule.end_datetime:
            return False, _("Schedule has ended")

        existing_dose = await self.get_current_dose(schedule.user, schedule)

        if not existing_dose.confirmed:
            dose = existing_dose
            dose.taken_datetime = datetime.now(timezone.utc)
            dose.confirmed = True
        else:
            return False, _("Dose already recorded")

        self.session.add(dose)
        await self.session.commit()

        return True, _("✅ Dose logged successfully for {drug_name}!").format(
            drug_name=schedule.drug_name,
        )

    # endregion

    # region Reports
    async def get_adherence_stats(self, user_id: int, days: int) -> dict:
        """Calculate medication adherence statistics for given period"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Get all schedules with doses in period
        stmt = (
            select(Schedule)
            .options(selectinload(Schedule.user))
            .where(
                Schedule.user_id == user_id,
                Schedule.start_datetime <= end_date,
                (Schedule.end_datetime >= start_date) | Schedule.end_datetime.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        schedules = result.scalars().all()

        # Get relevant doses in a single query using IN clause
        schedule_ids = [schedule.id for schedule in schedules]
        dose_stmt = (
            select(Dose)
            .where(
                Dose.schedule_id.in_(schedule_ids),
                Dose.taken_datetime >= start_date,
                Dose.taken_datetime <= end_date,
                Dose.confirmed,
            )
            .order_by(asc(Dose.taken_datetime))
        )
        dose_result = await self.session.execute(dose_stmt)
        all_doses = dose_result.scalars().all()

        # Group doses by schedule_id for efficient lookup
        doses_by_schedule = {}
        for dose in all_doses:
            if dose.schedule_id not in doses_by_schedule:
                doses_by_schedule[dose.schedule_id] = []
            doses_by_schedule[dose.schedule_id].append(dose)

        stats = {}

        for schedule in schedules:
            logger.debug("Process schedule %s", str(schedule))

            tz = pytz.timezone(schedule.user.timezone)
            expected_doses = self._calculate_expected_doses(
                schedule.user, schedule, start_date, end_date
            )

            actual_doses = doses_by_schedule.get(schedule.id, [])
            logger.debug("Actual doses: %s", str(actual_doses))

            on_time, late = self._categorize_doses(expected_doses, actual_doses, tz)
            taken = len(on_time) + len(late)
            missed = max(0, len(expected_doses) - taken)

            stats[schedule.drug_name] = {
                "dose": schedule.dose,
                "total": len(expected_doses),
                "taken": taken,
                "on_time": len(on_time),
                "late": len(late),
                "missed": missed,
                "percentage": (
                    round((taken / len(expected_doses)) * 100) if expected_doses else 0
                ),
            }

        return stats

    def _calculate_expected_doses(
        self,
        user: User,
        schedule: Schedule,
        start: datetime,
        end: datetime,
    ) -> list[datetime]:
        """Generate expected dose times in user's timezone"""
        # Don't calculate doses before schedule start
        effective_start = max(start, schedule.start_datetime)
        effective_end = min(end, schedule.end_datetime or end)

        # Convert to user's local dates
        local_start = user.in_local_time(effective_start).date()
        local_end = user.in_local_time(effective_end).date()
        days = (local_end - local_start).days

        times = self.get_doses_times(user, schedule)

        return [
            user.tz.localize(datetime.combine(local_start + timedelta(days=day), t))
            for day in range(days)
            for t in times
        ]

    def _categorize_doses(
        self,
        expected: list[datetime],
        actual: list[Dose],
        tz: pytz.BaseTzInfo,
    ):
        """Categorize doses as on-time or late"""
        on_time = []
        late = []
        tolerance = timedelta(minutes=30)

        if not expected:
            return on_time, late
        if not actual:
            return on_time, late

        idx = 0
        for dose in actual:
            dose_time = dose.taken_datetime.astimezone(tz)
            while True:
                if idx >= len(expected):
                    late.append(dose)
                    break

                expected_time = expected[idx]
                if (
                    abs((dose_time - expected_time).total_seconds())
                    <= tolerance.total_seconds()
                ):
                    on_time.append(dose)
                    break
                if expected_time > dose_time:
                    late.append(dose)
                    break

                idx += 1

        assert len(actual) == len(late) + len(on_time)

        return on_time, late

    # endregion
