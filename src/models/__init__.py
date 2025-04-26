import enum
from datetime import datetime
from functools import cached_property

import pytz
from sqlalchemy import CheckConstraint, Computed, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.connector import Base
from .mixins import TimedModelMixin
from .types import UTCDateTime
from .utils import default_now


class Role(enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"  # Optional for future admin roles


class User(Base, TimedModelMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        unique=True, nullable=False
    )  # Telegram user ID
    username: Mapped[str] = mapped_column(
        String(32), nullable=True
    )  # Telegram username (optional)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(32), default="UTC"
    )  # e.g., "Europe/Berlin"
    language_code: Mapped[str] = mapped_column(
        String(5), server_default="en", nullable=False
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=True
    )  # Optional for doctor-patient communication
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.PATIENT)

    privacy_accepted: Mapped[bool] = mapped_column(default=False)

    # Relationships
    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="user",
        lazy="select",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    doses: Mapped[list["Dose"]] = relationship(back_populates="user", lazy="select")

    @cached_property
    def tz(self) -> pytz.BaseTzInfo:
        return pytz.timezone(self.timezone)

    def in_local_time(self, dt: datetime) -> datetime:
        """Convert UTC datetime to user's local time"""
        return dt.astimezone(self.tz)


class Schedule(Base, TimedModelMixin):
    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("doses_per_day > 0", name="check_doses_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    drug_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dose: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # e.g., "10mg", "1 tablet"
    doses_per_day: Mapped[int] = mapped_column(nullable=False)
    duration: Mapped[int | None] = mapped_column(nullable=True)  # Duration in days
    comment: Mapped[str | None] = mapped_column(String(256), nullable=True)

    start_datetime: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True)
    )  # Actual start time after delay
    end_datetime: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True),
        Computed("start_datetime + INTERVAL duration DAY"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="schedules", lazy="select")
    doses: Mapped[list["Dose"]] = relationship(back_populates="schedule", lazy="select")

    def dose_interval_in_hours(self, daylight_hours: float) -> float:
        return daylight_hours / self.doses_per_day


class Dose(Base):
    __tablename__ = "doses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schedule_id: Mapped[int] = mapped_column(
        ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    taken_datetime: Mapped[datetime] = mapped_column(
        UTCDateTime(timezone=True), default=default_now
    )
    confirmed: Mapped[bool] = mapped_column(
        default=False
    )  # Mark if user skipped confirmation

    # Relationships
    user: Mapped["User"] = relationship(back_populates="doses", lazy="select")
    schedule: Mapped["Schedule"] = relationship(back_populates="doses", lazy="select")

    def __repr__(self) -> str:
        return f"<Dose id={self.id} taken={self.taken_datetime}>"
