"""Chrome History SQLite — snapshot + read-only search."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .date_filter import DateFilter


DEFAULT_HISTORY_PATH = Path.home() / "Library/Application Support/Google/Chrome/Default/History"
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
    """Snapshots Chrome's locked History sqlite to a tmp file, then searches it read-only."""

    _DATE_COLUMN_SQL = (
        "strftime('%Y-%m-%d %H:%M', last_visit_time/1000000 - 11644473600, "
        "'unixepoch', 'localtime')"
    )

    def __init__(self, source: Path = DEFAULT_HISTORY_PATH) -> None:
        self._source = source
        self._snapshot: Path | None = None

    @property
    def snapshot_path(self) -> Path | None:
        return self._snapshot

    def snapshot(self) -> Path:
        if not self._source.exists():
            raise FileNotFoundError(f"Chrome history not found at {self._source}")
        tmp = Path(tempfile.gettempdir()) / "chrome_history_tui.db"
        shutil.copyfile(self._source, tmp)
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
