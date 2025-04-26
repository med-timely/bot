from datetime import datetime, timezone
from sqlalchemy import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator):
    """
    A DateTime type which forces results to be timezone-aware in UTC,
    even if the database stores them as naive.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                # Convert aware datetime to UTC and remove timezone info
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            # If naive, assume it's UTC and proceed without modification
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            # Attach UTC timezone to the naive datetime from the database
            return value.replace(tzinfo=timezone.utc)
        return value
