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

    async def get_next_dose_time(
        self, user: User, schedule: Schedule
    ) -> Optional[datetime]:
        """Calculate the next dose time for a schedule, considering:
        - User's timezone
        - Daylight hours (8AM-8PM local time)
        - Already taken doses

        Args:
            schedule: The schedule to calculate for

        Returns:
            datetime of next dose in UTC, or None if schedule is complete
        """

        # Get user's timezone
        tz = pytz.timezone(user.timezone)

        # Convert current time to user's timezone
        now_utc = datetime.now(pytz.utc)
        now_local = now_utc.astimezone(tz)

        # Check if schedule has ended (in user's local time)
        if schedule.end_datetime is None:
            # If no end date, schedule is ongoing
            pass
        elif now_local > schedule.end_datetime.astimezone(tz):
            return None

        # Get all taken doses for this schedule (in UTC)
        doses = (
            (
                await self.session.execute(
                    select(Dose)
                    .where(Dose.schedule_id == schedule.id)
                    .order_by(Dose.taken_datetime)
                )
            )
            .scalars()
            .all()
        )

        if not doses:
            # First dose - use start time if within day hours
            start_local = schedule.start_datetime.astimezone(tz)
            return self._validate_next_local(start_local, tz)

        # Check if all doses have been taken
        if schedule.duration:
            total_doses = schedule.duration * schedule.doses_per_day
            if len(doses) >= total_doses:
                return None

        # Calculate next dose time (distributed evenly in 12-hour window)
        dose_interval = 12 / schedule.doses_per_day
        last_dose_local = doses[-1].taken_datetime.astimezone(tz)
        next_local = last_dose_local + timedelta(hours=dose_interval)

        # If next time would be at night, move to next morning
        next_local = self._validate_next_local(next_local, tz)

        # Check if this dose was already taken (within 1 hour window)
        next_utc = next_local.astimezone(pytz.utc)
        for dose in doses:
            if abs((dose.taken_datetime - next_utc).total_seconds()) < 3600:
                # Dose already taken - skip to next interval
                next_local += timedelta(hours=dose_interval)
                next_local = self._validate_next_local(next_local, tz)
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
