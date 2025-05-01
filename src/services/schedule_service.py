from datetime import datetime, time, timedelta, timezone
import logging
from typing import Optional

import pytz
from sqlalchemy import BooleanClauseList, asc, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from src.models import Dose, Schedule, User

logger = logging.getLogger(__name__)


class ScheduleService:
    DAY_START = time(8, 0)  # 8:00 AM local time
    DAY_END = time(20, 0)  # 8:00 PM local time

    def __init__(self, session: AsyncSession):
        self.session = session

    # region Create
    async def create_schedule(self, user_id: int, **data) -> Schedule:
        self._validate_schedule_data(data)

        fields = {k: v for k, v in data.items() if k in Schedule.__table__.columns}
        if "start_datetime" not in fields:
            fields["start_datetime"] = datetime.now(timezone.utc)

        schedule = Schedule(user_id=user_id, **fields)

        self.session.add(schedule)
        await self.session.commit()
        await self.session.refresh(schedule)
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

    # region Schedule Read
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
                        "UTC_TIMESTAMP() - INTERVAL :period / schedules.doses_per_day HOUR"
                    ).bindparams(period=(self.DAY_END.hour - self.DAY_START.hour) / 2),
                )
                .exists()
            )

        return base_filter

    # endregion

    # region Doses
    async def get_next_dose_time(
        self, user: User, schedule: Schedule
    ) -> Optional[datetime]:
        """Calculate the next dose time for a schedule, considering:
        - User's timezone
        - Daylight hours
        - Already taken doses

        Args:
            schedule: The schedule to calculate for

        Returns:
            datetime of next dose in UTC, or None if schedule is complete
        """

        # Convert current time to user's timezone
        now_utc = datetime.now(pytz.utc)
        now_local = user.in_local_time(now_utc)

        # Check if schedule has ended (in user's local time)
        if schedule.end_datetime is None:
            # If no end date, schedule is ongoing
            pass
        elif now_utc > schedule.end_datetime:
            return None

        # Get all taken doses for this schedule (in UTC)
        doses = sorted(
            (d for d in schedule.doses if d.confirmed), key=lambda d: d.taken_datetime
        )

        if not doses:
            # First dose in a day
            start_local = now_local
            return self._validate_next_local(start_local, user.tz)

        # Check if all doses have been taken
        if schedule.duration:
            total_doses = schedule.duration * schedule.doses_per_day
            if len(doses) >= total_doses:
                return None

        # Calculate next dose time (distributed evenly across day)
        dose_interval = schedule.dose_interval_in_hours(
            self.DAY_END.hour - self.DAY_START.hour
        )
        last_dose_local = user.in_local_time(doses[-1].taken_datetime)
        next_local = last_dose_local + timedelta(hours=dose_interval)

        # If next time would be at night, move to next morning
        next_local = self._validate_next_local(next_local, user.tz)

        # Check if this dose was already taken (within 1 hour window)
        next_utc = next_local.astimezone(pytz.utc)

        return self._find_next_available_dose_time(user, doses, next_utc, dose_interval)

    async def get_current_dose(self, schedule: Schedule) -> Dose:
        dose_interval = schedule.dose_interval_in_hours(
            self.DAY_END.hour - self.DAY_START.hour
        )
        window_start = datetime.now(timezone.utc) - timedelta(
            minutes=dose_interval * 60 / 2
        )
        whereclause = (Dose.schedule_id == schedule.id) & (
            Dose.taken_datetime >= window_start
        )
        existing_dose = (
            await self.session.execute(
                select(Dose)
                .where(whereclause)
                .order_by(Dose.taken_datetime.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if not existing_dose:
            return Dose(
                user_id=schedule.user_id,
                schedule_id=schedule.id,
                taken_datetime=datetime.now(timezone.utc),
                confirmed=False,
            )

        return existing_dose

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
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            return False, "Schedule not found or doesn't belong to you"

        if schedule.end_datetime and datetime.now(timezone.utc) > schedule.end_datetime:
            return False, "Schedule has ended"

        existing_dose = await self.get_current_dose(schedule)

        if not existing_dose.confirmed:
            dose = existing_dose
            dose.taken_datetime = datetime.now(timezone.utc)
            dose.confirmed = True
        else:
            return False, "Dose already recorded"

        self.session.add(dose)
        await self.session.commit()

        return True, f"✅ Dose logged successfully for {schedule.drug_name}!"

    def _validate_next_local(
        self, next_local: datetime, tz: pytz.BaseTzInfo
    ) -> datetime:
        if self.DAY_START <= next_local.time() <= self.DAY_END:
            return next_local

        next_day = next_local.date() + timedelta(days=1)
        next_local = tz.localize(datetime.combine(next_day, self.DAY_START))

        return next_local

    def _find_next_available_dose_time(
        self,
        user: User,
        doses: list[Dose],
        next_utc: datetime,
        dose_interval: float,
    ) -> datetime:
        # We round dose timestamps to tolerance windows (half the dose interval)
        # This allows us to detect if a proposed dose time overlaps with an already taken dose
        # even if the times don't match exactly
        tolerance_seconds = dose_interval / 2 * 3600

        # Create a set of rounded dose times for faster lookup
        rounded_dose_times = {
            round(dose.taken_datetime.timestamp() / tolerance_seconds) for dose in doses
        }

        next_local = user.in_local_time(next_utc)

        # Check if the proposed time overlaps with any taken dose
        while round(next_utc.timestamp() / tolerance_seconds) in rounded_dose_times:
            # Dose already taken - skip to next interval
            next_local += timedelta(hours=dose_interval)
            next_local = self._validate_next_local(next_local, user.tz)
            next_utc = next_local.astimezone(pytz.utc)

        return next_utc

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
                schedule, start_date, end_date, tz
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
        self, schedule: Schedule, start: datetime, end: datetime, tz: pytz.BaseTzInfo
    ) -> list[datetime]:
        """Generate expected dose times in user's timezone"""

        # Convert to user's local dates
        local_start = start.astimezone(tz).date()
        local_end = end.astimezone(tz).date()
        days = (local_end - local_start).days + 1

        daylight_hours = self.DAY_END.hour - self.DAY_START.hour
        interval_sec = daylight_hours * 3600 / schedule.doses_per_day

        expected: list[datetime] = []
        for day in range(days):
            base_date = local_start + timedelta(days=day)
            for i in range(schedule.doses_per_day):
                local_dt = datetime.combine(
                    base_date,
                    self.DAY_START,
                ) + timedelta(seconds=interval_sec * i)
                expected.append(tz.localize(local_dt))

        return [t for t in expected if start <= t <= end]

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
