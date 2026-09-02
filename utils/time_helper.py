"""
Timezone helpers.

All timestamps are persisted in UTC (see models.py `utcnow()`), but the business
day for a retail shop is a *local* day. Computing "today" with a naive local
`datetime.now()` and comparing it against UTC columns silently shifts every
daily KPI and report range by the UTC offset (5h30m for Asia/Kolkata).

These helpers convert local day boundaries into the UTC instants that bound
them, so date filters against stored UTC columns are correct.
"""

import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import LOCAL_TIMEZONE

try:
    LOCAL_TZ = ZoneInfo(LOCAL_TIMEZONE)
except (ZoneInfoNotFoundError, ValueError):
    LOCAL_TZ = datetime.timezone.utc


def utcnow() -> datetime.datetime:
    """Naive UTC timestamp, matching how columns are stored."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def local_now() -> datetime.datetime:
    """Naive local wall-clock time."""
    return datetime.datetime.now(LOCAL_TZ).replace(tzinfo=None)


def local_today() -> datetime.date:
    """Today's date in the shop's local timezone."""
    return datetime.datetime.now(LOCAL_TZ).date()


def local_date_to_utc(day: datetime.date, end_of_day: bool = False) -> datetime.datetime:
    """
    Convert a local calendar date into the naive UTC instant for its start
    (00:00:00 local) or its end (23:59:59.999999 local).
    """
    if end_of_day:
        naive_local = datetime.datetime.combine(day, datetime.time.max)
    else:
        naive_local = datetime.datetime.combine(day, datetime.time.min)
    aware_local = naive_local.replace(tzinfo=LOCAL_TZ)
    return aware_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def local_day_bounds_utc(day: datetime.date):
    """Return (start_utc, end_utc) covering one local calendar day."""
    return local_date_to_utc(day, False), local_date_to_utc(day, True)


def to_local(dt: datetime.datetime) -> datetime.datetime:
    """
    Render a stored (naive UTC) timestamp as naive local time for display.
    Passes through values that are already timezone-aware.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(LOCAL_TZ).replace(tzinfo=None)
