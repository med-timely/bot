from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytz

from src.models import Schedule, User
from src.services.schedule_service import ScheduleService


@pytest.fixture
def service():
    return ScheduleService(session=AsyncMock())


@pytest.fixture
def user():
    return User(
        id=1, timezone="Europe/Moscow", day_start=time(8, 0), day_end=time(20, 0)
    )


@pytest.fixture
def schedule(user):
    # Doses: 8:00, 14:00, 20:00 MSK
    #        5:00, 11:00, 17:00 UTC
    return Schedule(
        id=1,
        user_id=user.id,
        doses_per_day=3,
        dose=50,
        drug_name="TestDrug",
        start_datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        doses=[],
    )


@pytest.mark.asyncio
async def test_first_dose_calculation_within_daylight_hours(service, user, schedule):
    with patch(
        "src.services.schedule_service.datetime", wraps=datetime
    ) as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc)
        next_dose = await service.get_next_dose_time(user, schedule)

        # Verify next dose is current time
        assert next_dose == datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)


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
        (3, "09:00", "14:00"),  # +4h interval
        (4, "14:30", "20:00"),  # 17:30 Moscow (valid time)
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
        start_datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
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


@pytest.mark.asyncio
async def test_get_next_dose_time_before_schedule_start(service, user):
    # now is before schedule.start_datetime → first dose at 08:00 local on start date
    future = datetime(2024, 1, 2, tzinfo=timezone.utc)
    sched = Schedule(
        id=2, user_id=user.id, doses_per_day=2, start_datetime=future, doses=[]
    )
    with patch("src.services.schedule_service.datetime", wraps=datetime) as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 7, tzinfo=timezone.utc)
        nxt = await service.get_next_dose_time(user, sched)
    local = nxt.astimezone(pytz.timezone(user.timezone))
    assert local.date() == future.date()
    assert local.hour == 8


@pytest.mark.asyncio
async def test_get_next_dose_time_handles_unknown_timezone(service, schedule):
    # invalid timezone string → pytz.UnknownTimeZoneError
    bad_user = User(id=99, timezone="Invalid/Zone")
    with patch("src.services.schedule_service.datetime", wraps=datetime) as mock_dt:
        mock_dt.now.return_value = datetime(2024, 1, 1, 7, tzinfo=timezone.utc)
        with pytest.raises(pytz.UnknownTimeZoneError):
            await service.get_next_dose_time(bad_user, schedule)


@pytest.mark.asyncio
async def test_create_schedule_error(service, schedule):
    service.session.commit.side_effect = Exception("Create failed")
    with pytest.raises(Exception):
        await service.create_schedule(schedule)


def test_get_doses_times_one_dose_per_day(service, user, schedule):
    """Test that get_doses_times returns the correct time for one dose per day."""
    schedule.doses_per_day = 1
    times = service.get_doses_times(user, schedule)
    assert times == [user.day_start]


def test_get_doses_times_two_doses_per_day(service, user, schedule):
    """Test that get_doses_times returns the correct times for two doses per day."""
    schedule.doses_per_day = 2
    times = service.get_doses_times(user, schedule)
    assert times == [user.day_start, user.day_end]


def test_get_doses_times_multiple_doses_per_day(service, user, schedule):
    """Test that get_doses_times returns evenly spaced times for multiple doses per day."""
    schedule.doses_per_day = 4
    times = service.get_doses_times(user, schedule)

    expected_times = [
        user.day_start,
        user.day_start.replace(hour=user.day_start.hour + 4),
        user.day_start.replace(hour=user.day_start.hour + 8),
        user.day_start.replace(hour=user.day_start.hour + 12),
    ]

    assert times == expected_times


def test_calculate_expected_doses_one_day(service, user, schedule):
    """Test _calculate_expected_doses for a single day."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 23, 59, 59, tzinfo=timezone.utc)

    expected_doses = service._calculate_expected_doses(user, schedule, start, end)

    # For 3 doses per day, we should get 3 doses on the same day
    assert len(expected_doses) == 3

    # All doses should be on the same day
    assert all(d.date() == datetime(2024, 1, 1).date() for d in expected_doses)

    # Check that the times match the expected dose times
    expected_times = [
        time(8, 0),
        time(14, 0),
        time(20, 0),
    ]
    assert [d.time() for d in expected_doses] == expected_times


def test_calculate_expected_doses_multiple_days(service, user, schedule):
    """Test _calculate_expected_doses for multiple days."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 3, 23, 59, 59, tzinfo=timezone.utc)

    expected_doses = service._calculate_expected_doses(user, schedule, start, end)

    # For 3 doses per day over 3 days, we should get 9 doses
    assert len(expected_doses) == 9

    # Check that we have doses for all 3 days
    dates = {d.date() for d in expected_doses}
    expected_dates = {
        datetime(2024, 1, 1).date(),
        datetime(2024, 1, 2).date(),
        datetime(2024, 1, 3).date(),
    }
    assert dates == expected_dates

    # Check that each day has the correct number of doses
    for date in expected_dates:
        daily_doses = [d for d in expected_doses if d.date() == date]
        assert len(daily_doses) == 3

        # Check that the times match the expected dose times
        expected_times = [
            time(8, 0),
            time(14, 0),
            time(20, 0),
        ]
        assert [d.time() for d in daily_doses] == expected_times


def test_calculate_expected_doses_before_schedule_start(service, user, schedule):
    """Test _calculate_expected_doses when start is before schedule start."""
    # Move schedule start to 2024-01-02
    schedule.start_datetime = datetime(2024, 1, 2, tzinfo=timezone.utc)

    # Request doses from 2024-01-01 to 2024-01-01
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 1, 23, 59, 59, tzinfo=timezone.utc)

    expected_doses = service._calculate_expected_doses(user, schedule, start, end)

    # Should be empty since it's before schedule start
    assert len(expected_doses) == 0


def test_calculate_expected_doses_after_schedule_end(service, user, schedule):
    """Test _calculate_expected_doses when end is after schedule end."""
    # Set schedule to end on 2024-01-02
    schedule.end_datetime = datetime(2024, 1, 2, tzinfo=timezone.utc)

    # Request doses from 2024-01-03 to 2024-01-03
    start = datetime(2024, 1, 3, tzinfo=timezone.utc)
    end = datetime(2024, 1, 3, 23, 59, 59, tzinfo=timezone.utc)

    expected_doses = service._calculate_expected_doses(user, schedule, start, end)

    # Should be empty since it's after schedule end
    assert len(expected_doses) == 0
