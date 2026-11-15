"""Five-field cron expressions for scheduled runs: `minute hour day-of-month month day-of-week`.

Each field takes `*`, numbers, ranges `a-b`, lists `a,b` and steps `*/n` or `a-b/n`. Months and weekdays also take names
(`JAN`, `MON`); weekday 0 and 7 are Sunday. As in classic cron, when both day fields are restricted a day matches if
either does. Macros: @yearly, @monthly, @weekly, @daily, @hourly. Times are wall-clock times in a IANA time zone; a time
that a DST change skips runs an hour later, and one it repeats runs once.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, NamedTuple, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MACROS = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *", "@weekly": "0 0 * * 0",
          "@daily": "0 0 * * *", "@midnight": "0 0 * * *", "@hourly": "0 * * * *"}
MONTHS = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
DAYS = {d: i for i, d in enumerate("SUN MON TUE WED THU FRI SAT".split())}
# (name, low, high, names)
FIELDS = (("minute", 0, 59, {}), ("hour", 0, 23, {}), ("day of month", 1, 31, {}), ("month", 1, 12, MONTHS), ("day of week", 0, 7, DAYS))


class CronError(ValueError):
    """Why an expression or time zone is invalid (the message names the field)."""


class Cron(NamedTuple):
    minutes: frozenset; hours: frozenset; days: frozenset; months: frozenset; weekdays: frozenset
    any_day: bool; any_weekday: bool


def _num(tok: str, names: dict, name: str) -> int:
    t = tok.upper()
    if t in names: return names[t]
    if not t.isdigit(): raise CronError(f"{name}: '{tok}' is not a number")
    return int(t)


def _field(text: str, name: str, lo: int, hi: int, names: dict) -> frozenset:
    out = set()
    for part in text.split(","):
        rng, _, step = part.partition("/")
        if step and (not step.isdigit() or int(step) == 0): raise CronError(f"{name}: step '{step}' must be a positive number")
        if rng == "*": a, b = lo, hi
        elif "-" in rng: a, b = (_num(x, names, name) for x in rng.split("-", 1))
        else: a = b = _num(rng, names, name); b = hi if step else b  # `5/15` means from 5 to the end
        if not lo <= a <= hi or not lo <= b <= hi: raise CronError(f"{name}: values must be {lo}-{hi}")
        if a > b: raise CronError(f"{name}: range {a}-{b} goes backwards")
        out.update(range(a, b + 1, int(step) if step else 1))
    if not out: raise CronError(f"{name}: no value")
    return frozenset(out)


def parse(expr: str) -> Cron:
    text = MACROS.get((expr or "").strip().lower(), (expr or "").strip())
    parts = text.split()
    if len(parts) != 5: raise CronError("use five fields: minute hour day-of-month month day-of-week")
    sets = [_field(p, *f) for p, f in zip(parts, FIELDS)]
    weekdays = frozenset(d % 7 for d in sets[4])  # 7 is Sunday too
    return Cron(sets[0], sets[1], sets[2], sets[3], weekdays, parts[2] == "*", parts[4] == "*")


def zone(name: str) -> ZoneInfo:
    try: return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError): raise CronError(f"unknown time zone '{name}'") from None


def _day_ok(c: Cron, d: datetime) -> bool:
    dom, dow = d.day in c.days, (d.weekday() + 1) % 7 in c.weekdays  # Python Monday=0 -> cron Monday=1
    if c.any_day and c.any_weekday: return True
    if c.any_day: return dow
    if c.any_weekday: return dom
    return dom or dow


def next_time(c: Cron, tz: ZoneInfo, after: float) -> Optional[float]:
    """The first matching wall-clock minute strictly after `after` (epoch seconds), as epoch seconds; None if none in 5 years."""
    day = datetime.fromtimestamp(after, tz).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    for _ in range(366 * 5):
        if day.month in c.months and _day_ok(c, day):
            for h in sorted(c.hours):
                for m in sorted(c.minutes):
                    local = day.replace(hour=h, minute=m)
                    ts = local.replace(tzinfo=tz).timestamp()  # fold=0: a repeated hour runs once, a skipped one an hour later
                    if ts > after: return ts
        day += timedelta(days=1)
    return None


def upcoming(expr: str, tz_name: str, after: float, n: int = 5) -> List[float]:
    c, tz, out = parse(expr), zone(tz_name), []
    while len(out) < n and (t := next_time(c, tz, out[-1] if out else after)) is not None: out.append(t)
    return out
