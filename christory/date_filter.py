"""DateFilter — owns the YYYY[-MM[-DD]] [.. YYYY-MM-DD] grammar."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


class _Kind(Enum):
    EMPTY = "empty"
    PREFIX = "prefix"
    RANGE = "range"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class DateFilter:
    kind: _Kind
    raw: str = ""
    prefix: str = ""
    start_input: str = ""
    end_input: str = ""

    @classmethod
    def parse(cls, value: str) -> "DateFilter":
        raw = value.strip()
        if not raw:
            return cls(kind=_Kind.EMPTY)
        if ".." in raw:
            a, _, b = raw.partition("..")
            a, b = a.strip(), b.strip()
            sd = _parse_date_input(a) if a else None
            ed = _parse_date_input(b) if b else None
            if (a and sd is None) or (b and ed is None):
                return cls(kind=_Kind.INVALID, raw=raw)
            return cls(kind=_Kind.RANGE, raw=raw, start_input=a, end_input=b)
        if _parse_date_input(raw) is None:
            return cls(kind=_Kind.INVALID, raw=raw)
        return cls(kind=_Kind.PREFIX, raw=raw, prefix=raw)

    @classmethod
    def from_range(cls, start: date | None, end: date | None) -> "DateFilter":
        """Build a filter from picker selections. Single-day collapses to PREFIX."""
        if start is None and end is None:
            return cls(kind=_Kind.EMPTY)
        s = start.strftime("%Y-%m-%d") if start else ""
        e = end.strftime("%Y-%m-%d") if end else ""
        if s and e:
            lo, hi = sorted([s, e])
            if lo == hi:
                return cls(kind=_Kind.PREFIX, raw=lo, prefix=lo)
            return cls(kind=_Kind.RANGE, raw=f"{lo}..{hi}", start_input=lo, end_input=hi)
        return cls(kind=_Kind.RANGE, raw=f"{s}..{e}", start_input=s, end_input=e)

    def to_sql(self, params: dict[str, Any], *, column: str) -> str:
        """Render a SQL boolean fragment; mutate params with bind vars. '' if no constraint."""
        if self.kind is _Kind.EMPTY:
            return ""
        if self.kind is _Kind.INVALID:
            return "0 = 1"
        if self.kind is _Kind.PREFIX:
            params["date"] = f"{self.prefix}%"
            return f"{column} LIKE :date"
        parts: list[str] = []
        if self.start_input:
            params["date_start"] = _expand_partial(self.start_input, end_of=False)
            parts.append(f"{column} >= :date_start")
        if self.end_input:
            params["date_end"] = _expand_partial(self.end_input, end_of=True)
            parts.append(f"{column} <= :date_end")
        return " AND ".join(parts)

    def to_input_string(self) -> str:
        """The string the filter Input should display."""
        if self.kind is _Kind.RANGE:
            s, e = self.start_input, self.end_input
            if s and e:
                return s if s == e else f"{s}..{e}"
            if s:
                return f"{s}.."
            if e:
                return f"..{e}"
            return ""
        return self.raw

    def calendar_seed(self) -> tuple[date | None, date | None, date | None]:
        """(cursor, start, end) — picker opens reflecting the current filter."""
        if self.kind is _Kind.RANGE:
            sd = _parse_date_input(self.start_input) if self.start_input else None
            ed = _parse_date_input(self.end_input) if self.end_input else None
            return (ed or sd), sd, ed
        if self.kind is _Kind.PREFIX:
            d = _parse_date_input(self.prefix)
            return d, d, d
        return None, None, None


def _parse_date_input(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _expand_partial(value: str, *, end_of: bool) -> str | None:
    """YYYY / YYYY-MM / YYYY-MM-DD -> inclusive period boundary as 'YYYY-MM-DD HH:MM'."""
    for fmt, kind in (("%Y-%m-%d", "day"), ("%Y-%m", "month"), ("%Y", "year")):
        try:
            d = datetime.strptime(value, fmt).date()
        except ValueError:
            continue
        if kind == "day":
            return f"{d.strftime('%Y-%m-%d')} {'23:59' if end_of else '00:00'}"
        if kind == "month":
            if end_of:
                last = calendar.monthrange(d.year, d.month)[1]
                return f"{d.year:04d}-{d.month:02d}-{last:02d} 23:59"
            return f"{d.year:04d}-{d.month:02d}-01 00:00"
        return f"{d.year:04d}-12-31 23:59" if end_of else f"{d.year:04d}-01-01 00:00"
    return None
