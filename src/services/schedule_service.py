from datetime import datetime, time, timedelta, timezone
from typing import Optional

import pytz
from sqlalchemy import BooleanClauseList, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from src.models import Dose, Schedule, User


class ScheduleService:
    DAY_START = time(8, 0)  # 8:00 AM local time
    DAY_END = time(20, 0)  # 8:00 PM local time

    def __init__(self, session: AsyncSession):
        self.session = session

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

    def _validate_schedule_data(self, data):
        required = ["drug_name", "dose", "doses_per_day"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if data["doses_per_day"] < 1:
            raise ValueError("Frequency must be positive number")

        if "duration" in data and data["duration"] is not None and data["duration"] < 1:
            raise ValueError("Duration must be a positive number or not specified")
