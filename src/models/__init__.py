import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, Computed, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.connector import Base
from .mixins import TimedModelMixin
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
        DateTime(timezone=True)
    )  # Actual start time after delay
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        Computed("start_datetime + INTERVAL duration DAY"),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="schedules", lazy="joined")
    doses: Mapped[list["Dose"]] = relationship(back_populates="schedule", lazy="select")


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
        DateTime(timezone=True), default=default_now
    )
    confirmed: Mapped[bool] = mapped_column(
        default=False
    )  # Mark if user skipped confirmation

    # Relationships
    user: Mapped["User"] = relationship(back_populates="doses", lazy="joined")
    schedule: Mapped["Schedule"] = relationship(back_populates="doses", lazy="joined")
