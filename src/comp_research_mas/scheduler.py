from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .orchestrator import run_monthly_orchestrator


def first_monday(year: int, month: int) -> date:
    d = date(year, month, 1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def is_monthly_run_day(day: date | None = None) -> bool:
    day = day or date.today()
    return day == first_monday(day.year, day.month)


def period_id_for(day: date | None = None) -> str:
    day = day or date.today()
    return f"{day.year}-{day.month:02d}"


def run_monthly(*, period_id: str | None = None, manual: bool = False, today: date | None = None) -> dict[str, Any]:
    pid = period_id or period_id_for(today)
    if not manual and not is_monthly_run_day(today):
        return {"status": "skipped", "period_id": pid, "reason": "not first Monday"}
    return run_monthly_orchestrator(period_id=pid, manual=manual)
