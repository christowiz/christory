"""Chromium History SQLite — snapshot + read-only search for any Chromium browser."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .browsers import Browser, default as default_browser
from .date_filter import DateFilter


DEFAULT_HISTORY_PATH = default_browser().history_path
WEBKIT_EPOCH_OFFSET = 11_644_473_600
ROW_LIMIT = 10_000


@dataclass(frozen=True, slots=True)
class HistoryRow:
    visited: str
    visits: int
    title: str
    url: str

    def format_info(self) -> str:
        return (
            f"Title: {self.title}\n"
            f"URL: {self.url}\n"
            f"Visited: {self.visited}\n"
            f"Visits: {self.visits}"
        )


class HistoryDatabase:
    """Snapshots a Chromium browser's locked History sqlite to tmp, then searches it read-only."""

    _DATE_COLUMN_SQL = (
        "strftime('%Y-%m-%d %H:%M', last_visit_time/1000000 - 11644473600, "
        "'unixepoch', 'localtime')"
    )

    def __init__(self, browser: Browser | None = None) -> None:
        self._browser = browser or default_browser()
        self._snapshot: Path | None = None

    @property
    def browser(self) -> Browser:
        return self._browser

    @property
    def snapshot_path(self) -> Path | None:
        return self._snapshot

    def set_browser(self, browser: Browser) -> None:
        self._browser = browser
        self._snapshot = None

    def snapshot(self) -> Path:
        source = self._browser.history_path
        if not source.exists():
            raise FileNotFoundError(
                f"{self._browser.label} history not found at {source}"
            )
        tmp = Path(tempfile.gettempdir()) / f"christory_{self._browser.key}.db"
        shutil.copyfile(source, tmp)
        self._snapshot = tmp
        return tmp

    def search(
        self,
        text: str,
        domain: str,
        date_filter: DateFilter,
        limit: int = ROW_LIMIT,
    ) -> list[HistoryRow]:
        if self._snapshot is None:
            raise RuntimeError("snapshot() must be called before search()")
        where_parts = [
            "(url LIKE :text OR title LIKE :text)",
            "url LIKE :domain",
        ]
        params: dict = {
            "text": f"%{text}%",
            "domain": f"%{domain}%",
            "limit": limit,
        }
        date_sql = date_filter.to_sql(params, column=self._DATE_COLUMN_SQL)
        if date_sql:
            where_parts.append(date_sql)

        sql = (
            "SELECT last_visit_time, visit_count, COALESCE(title, ''), url\n"
            "FROM urls\n"
            f"WHERE {' AND '.join(where_parts)}\n"
            "ORDER BY last_visit_time DESC\n"
            "LIMIT :limit"
        )
        with sqlite3.connect(f"file:{self._snapshot}?mode=ro", uri=True) as conn:
            return [
                HistoryRow(
                    visited=_webkit_to_local(ts),
                    visits=count,
                    title=title,
                    url=url,
                )
                for ts, count, title, url in conn.execute(sql, params)
            ]


def _webkit_to_local(webkit_us: int) -> str:
    if not webkit_us:
        return ""
    return datetime.fromtimestamp(
        webkit_us / 1_000_000 - WEBKIT_EPOCH_OFFSET
    ).strftime("%Y-%m-%d %H:%M")
