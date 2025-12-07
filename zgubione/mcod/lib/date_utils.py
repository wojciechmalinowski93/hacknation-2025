from datetime import date, datetime, time, tzinfo
from typing import Optional


def date_at_midnight(dt: date, tz: Optional[tzinfo] = None) -> datetime:
    """Construct a datetime with a midnight from the given `dt` date
    (naive if the time zone `tz` is `None`).
    """
    naive_dt = datetime.combine(dt, time(0, 0))
    if tz is None:
        return naive_dt
    return tz.localize(naive_dt)
