import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from src.services.schedule_service import ScheduleService
from src.models import User, Schedule
import pytz


@pytest.fixture
def service():
    return ScheduleService(session=AsyncMock())


@pytest.fixture
def user():
    return User(id=1, timezone="Europe/Moscow")


@pytest.fixture
def schedule(user):
    return Schedule(
        id=1,
        user_id=user.id,
        doses_per_day=3,
        dose=50,
        drug_name="TestDrug",
        start_datetime=datetime(2024, 1, 1),
        doses=[],
    )


@pytest.mark.asyncio
async def test_first_dose_calculation_within_daylight_hours(service, user, schedule):
    # Mock current time to 2024-01-01 07:00 UTC (10:00 AM Moscow time)
    with patch(
        "src.services.schedule_service.datetime", wraps=datetime
    ) as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 7, 0, tzinfo=timezone.utc)
        next_dose = await service.get_next_dose_time(user, schedule)

        # Verify next dose is current time
        assert next_dose == datetime(2024, 1, 1, 7, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "doses_per_day,expected_local_hour",
    [
        (1, 8),  # 1 dose/day at 8:00 AM
        (3, 8),  # 3 doses/day - first dose at 8:00 AM
        (4, 8),  # 4 doses/day - first dose at 8:00 AM
    ],
)
@pytest.mark.asyncio
async def test_first_dose_time(doses_per_day, expected_local_hour, service, user):
    schedule = Schedule(
        doses_per_day=doses_per_day,
        start_datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        doses=[],
    )

    with patch(
        "src.services.schedule_service.datetime", wraps=datetime
    ) as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 5, 0, tzinfo=timezone.utc)
        next_dose = await service.get_next_dose_time(user, schedule)
        local_time = next_dose.astimezone(pytz.timezone(user.timezone))

        assert local_time.hour == expected_local_hour


@pytest.mark.asyncio
async def test_schedule_expiration(service, user):
    # Create expired schedule
    schedule = Schedule(
        doses_per_day=3,
        start_datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_datetime=datetime(2024, 1, 2, tzinfo=timezone.utc),
        doses=[],
    )

    with patch(
        "src.services.schedule_service.datetime", wraps=datetime
    ) as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 3, tzinfo=timezone.utc)
        next_dose = await service.get_next_dose_time(user, schedule)

        assert next_dose is None


@pytest.mark.parametrize(
    "doses_per_day, test_time_utc, expected_local_time",
    [
        (1, "04:30", "08:00"),  # 07:30 Moscow → adjusted to 08:00
        (1, "05:00", "08:00"),  # 08:00 Moscow (exact start)
        (3, "05:00", "08:00"),  # First dose
        (3, "09:00", "12:00"),  # +4h interval
        (4, "14:30", "17:30"),  # 17:30 Moscow (valid time)
        (6, "17:15", "08:00+1d"),  # 20:15 Moscow → next day
    ],
)
@pytest.mark.asyncio
async def test_dose_intervals(
    doses_per_day, test_time_utc, expected_local_time, service, user
):
    # Convert UTC test time to datetime
    test_hour, test_minute = map(int, test_time_utc.split(":"))
    mock_utc = datetime(2024, 1, 1, test_hour, test_minute, tzinfo=timezone.utc)

    schedule = Schedule(
        doses_per_day=doses_per_day,
        start_datetime=datetime(2024, 1, 1),
        doses=[],
    )

    with patch(
        "src.services.schedule_service.datetime", wraps=datetime
    ) as mock_datetime:
        mock_datetime.now.return_value = mock_utc
        next_dose = await service.get_next_dose_time(user, schedule)
        local_time = next_dose.astimezone(pytz.timezone(user.timezone))

        # Verify time format
        time_str = local_time.strftime("%H:%M")
        if "+1d" in expected_local_time:
            assert local_time.date() == datetime(2024, 1, 2).date()
            time_str += "+1d"

        assert time_str == expected_local_time
