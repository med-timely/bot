from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from .types import UTCDateTime
from .utils import default_now


class TimedModelMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), default=default_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True),
        default=default_now,
        onupdate=default_now,
        nullable=False,
    )
