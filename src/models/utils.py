from datetime import datetime, timezone
import functools


default_now = functools.partial(datetime.now, timezone.utc)
