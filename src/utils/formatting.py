from datetime import date, datetime, time
from typing import Literal, Optional

from aiogram.utils.i18n import get_i18n
from babel.dates import format_date as fd
from babel.dates import format_datetime as fdt
from babel.dates import format_time as ft

Format = Literal["full", "long", "medium", "short"]


def format_date(
    dt: date | datetime, format: Format = "long", locale: Optional[str] = None
):
    """Format date using locale-aware formatting"""
    if not locale:
        i18n = get_i18n()
        locale = i18n.current_locale or "en"
    return fd(dt, format=format, locale=locale)


def format_time(
    dt: time | datetime, format: Format = "short", locale: Optional[str] = None
):
    """Format date using locale-aware formatting"""
    if not locale:
        i18n = get_i18n()
        locale = i18n.current_locale or "en"
    return ft(dt, format=format, locale=locale)


def format_datetime(
    dt: datetime, format: Format = "short", locale: Optional[str] = None
):
    """Format date using locale-aware formatting"""
    if not locale:
        i18n = get_i18n()
        locale = i18n.current_locale or "en"
    return fdt(dt, format=format, locale=locale)
