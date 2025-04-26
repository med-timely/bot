from datetime import datetime, time, timedelta, timezone
from typing import Optional

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def get_active_schedules(self, user_id: int) -> list[Schedule]:
        """Get all active schedules for a user"""
        now = datetime.now(timezone.utc)

        stmt = (
            select(Schedule)
            .where(
                Schedule.user_id == user_id,
                # Either ongoing (no end date) or not yet ended
                ((Schedule.end_datetime.is_(None)) | (Schedule.end_datetime > now)),
            )
            .order_by(Schedule.start_datetime)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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
        elif now_local > user.in_local_time(schedule.end_datetime):
            return None

        # Get all taken doses for this schedule (in UTC)
        doses = (
            (
                await self.session.execute(
                    select(Dose)
                    .where(
                        Dose.schedule_id == schedule.id,
                        Dose.taken_datetime >= now_utc.date(),
                    )
                    .order_by(Dose.taken_datetime)
                )
            )
            .scalars()
            .all()
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

        # Calculate next dose time (distributed evenly in 12-hour window)
        dose_interval = (
            self.DAY_END.hour - self.DAY_START.hour
        ) / schedule.doses_per_day
        last_dose_local = user.in_local_time(doses[-1].taken_datetime)
        next_local = last_dose_local + timedelta(hours=dose_interval)

        # If next time would be at night, move to next morning
        next_local = self._validate_next_local(next_local, user.tz)

        # Check if this dose was already taken (within 1 hour window)
        next_utc = next_local.astimezone(pytz.utc)

        # Create a set of rounded dose times for faster lookup
        rounded_dose_times = {
            round(dose.taken_datetime.timestamp() / 3600) for dose in doses
        }

        # Check if the proposed time overlaps with any taken dose
        while round(next_utc.timestamp() / 3600) in rounded_dose_times:
            # Dose already taken - skip to next interval
            next_local += timedelta(hours=dose_interval)
            next_local = self._validate_next_local(next_local, user.tz)
            next_utc = next_local.astimezone(pytz.utc)

        return next_utc

    def _validate_next_local(
        self, next_local: datetime, tz: pytz.BaseTzInfo
    ) -> datetime:
        if self.DAY_START <= next_local.time() <= self.DAY_END:
            return next_local

        next_day = next_local.date() + timedelta(days=1)
        next_local = tz.localize(datetime.combine(next_day, self.DAY_START))

        return next_local

    def _validate_schedule_data(self, data):
        required = ["drug_name", "dose", "doses_per_day"]
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        if data["doses_per_day"] < 1:
            raise ValueError("Frequency must be positive number")

        if "duration" in data and data["duration"] is not None and data["duration"] < 1:
            raise ValueError("Duration must be a positive number or not specified")
