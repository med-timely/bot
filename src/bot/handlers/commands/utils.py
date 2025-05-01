from datetime import datetime, timedelta

import pytz


def round_to_nearest_15_minutes(value: float) -> float:
    """Round to nearest 15 minutes (0.25 hours)"""
    return round(value * 4) / 4


def calculate_timezone_from_time(
    user_time: str, utc_now: datetime
) -> tuple[list[str] | None, float | None]:
    """Convert local time input to possible timezones"""
    try:
        # Parse user input with flexible format
        user_time = user_time.replace(".", ":").replace(",", ":")
        if ":" not in user_time:
            user_time += ":00"

        hours, minutes = map(int, user_time.split(":"))
        if not (0 <= hours < 24 and 0 <= minutes < 60):
            raise ValueError

        # Calculate offset from UTC handling day wrap-around
        local_dt = datetime.combine(utc_now.date(), datetime.min.time()) + timedelta(
            hours=hours, minutes=minutes
        )
        local_dt = local_dt.replace(tzinfo=pytz.utc)  # Make local_dt offset-aware
        offset = local_dt - utc_now
        offset_hours = offset.total_seconds() / 3600

        # Normalize offset to valid UTC range (-12 to +14 hours)
        offset_hours = (offset_hours + 12) % 24 - 12

        # Find matching timezones (consider DST)
        matching_zones: list[str] = []
        for tz_name in pytz.all_timezones:
            tz = pytz.timezone(tz_name)
            local_now = utc_now.astimezone(tz)
            current_offset = local_now.utcoffset().total_seconds() / 3600  # type: ignore
            if (
                abs(
                    round_to_nearest_15_minutes(current_offset)
                    - round_to_nearest_15_minutes(offset_hours)
                )
                < 0.001
            ):
                matching_zones.append(tz_name)

        return matching_zones, offset_hours

    except (ValueError, IndexError):
        return None, None
