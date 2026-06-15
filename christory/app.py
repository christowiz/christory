"""Chrome history search TUI — app shell and entry point."""
from __future__ import annotations

import webbrowser

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import DataTable, Header, Input, Static

from .config import (
    APP_CSS,
    DISPLAY_LABELS,
    HELP_TEXT,
    MIN_TEXT_WIDTH,
    SHOW_VISITS,
    SORT_ASC_ARROW,
    SORT_COLUMNS,
    SORT_DESC_ARROW,
    VISITED_WIDTH,
    VISITS_WIDTH,
)
from .date_filter import DateFilter
from .db import HistoryDatabase, HistoryRow
from .widgets import DatePickerScreen, FilterInput, HistoryTable, InfoScreen


class ChromeHistoryApp(App):
    TITLE = "Chrome History Search"
    BINDINGS = [
        Binding("ctrl+c", "quit", show=False, priority=True),
        Binding("ctrl+q", "noop", show=False, priority=True),
    ]
    CSS = APP_CSS

    def __init__(self) -> None:
        super().__init__()
        self.db = HistoryDatabase()
        self._resize_debounce = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            FilterInput(placeholder="search text…  (/ to focus)", id="search"),
            FilterInput(placeholder="domain…  e.g. github.com", id="domain"),
            FilterInput(placeholder="date…  e.g. 2026-05-20 or 2026-05-20..2026-05-25", id="date"),
            id="filter-bar",
        )
        yield Static("", id="status")
        yield HistoryTable(id="results", cursor_type="row", zebra_stripes=True)
        yield Static(HELP_TEXT, id="help")

    def on_mount(self) -> None:
        table = self.query_one(HistoryTable)
        table.col_keys["visited"] = table.add_column(
            DISPLAY_LABELS["visited"], width=VISITED_WIDTH, key="visited"
        )
        if SHOW_VISITS:
            table.col_keys["visits"] = table.add_column(
                DISPLAY_LABELS["visits"], width=VISITS_WIDTH, key="visits"
            )
        table.col_keys["title"] = table.add_column(
            DISPLAY_LABELS["title"], width=table.title_width, key="title"
        )
        table.col_keys["url"] = table.add_column(
            DISPLAY_LABELS["url"], width=table.url_width, key="url"
        )
        table.update_sort_indicators()
        self.action_refresh()
        self.query_one("#search", Input).focus()
        self.call_after_refresh(self._resize_text_columns)

    def on_resize(self, event) -> None:
        if self._resize_debounce:
            self._resize_debounce.stop()
        self._resize_debounce = self.set_timer(0.1, self._resize_text_columns)

    def _resize_text_columns(self) -> None:
        table = self.query_one(HistoryTable)
        if not table.col_keys.get("title") or not table.col_keys.get("url"):
            return
        width = table.size.width
        if width <= 0:
            return
        n_cols = 2 + (1 if SHOW_VISITS else 0) + 2
        # column gutters + a couple cells for cursor / scrollbar
        overhead = (n_cols - 1) + 2
        fixed = VISITED_WIDTH + (VISITS_WIDTH if SHOW_VISITS else 0)
        flex = max(MIN_TEXT_WIDTH * 2, width - overhead - fixed)
        title_w = max(MIN_TEXT_WIDTH, int(flex * 0.35))
        url_w = max(MIN_TEXT_WIDTH, flex - title_w)
        table.set_text_widths(title_w, url_w)

    def action_refresh(self) -> None:
        status = self.query_one("#status", Static)
        try:
            self.db.snapshot()
            self.run_search()
        except FileNotFoundError as e:
            status.update(f"[red]{e}[/red]")

    def update_sort_status(self) -> None:
        table = self.query_one(HistoryTable)
        col = DISPLAY_LABELS[SORT_COLUMNS[table.sort_index]]
        arrow = SORT_DESC_ARROW if table.sort_descending else SORT_ASC_ARROW
        n = table.row_count
        self.query_one("#status", Static).update(
            f"{n} result(s)  ·  sort: {col} {arrow}  ·  snapshot: {self.db.snapshot_path}"
        )

    def run_search(self) -> None:
        if self.db.snapshot_path is None:
            return
        text = self.query_one("#search", Input).value.strip()
        domain = self.query_one("#domain", Input).value.strip()
        date_filter = DateFilter.parse(self.query_one("#date", Input).value)
        rows = self.db.search(text, domain, date_filter)
        table = self.query_one(HistoryTable)
        table.marquee.detach()
        table.clear()
        table.full_rows.clear()
        for row in rows:
            cells = [row.visited]
            if SHOW_VISITS:
                cells.append(str(row.visits))
            cells.append(row.title[: table.title_width])
            cells.append(row.url[: table.url_width])
            key = table.add_row(*cells)
            table.full_rows[key] = row
        if not (table.sort_index == 0 and table.sort_descending):
            table.apply_sort()
        self.update_sort_status()
        if table.row_count:
            table.move_cursor(row=0, animate=False)
            table.attach_marquee_to_cursor()

    @on(Input.Changed)
    def _filter_changed(self, event: Input.Changed) -> None:
        self.run_search()

    @on(Input.Submitted)
    def _input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "date":
            cursor, start, end = DateFilter.parse(event.value).calendar_seed()
            self._open_modal(
                DatePickerScreen(
                    initial=cursor,
                    initial_start=start,
                    initial_end=end,
                    on_filter_change=self._apply_date_filter,
                ),
            )
        else:
            self.query_one(HistoryTable).focus()

    def _apply_date_filter(self, value: str) -> None:
        self.query_one("#date", Input).value = value

    @on(DataTable.RowSelected)
    def _row_selected(self, event: DataTable.RowSelected) -> None:
        row = self.query_one(HistoryTable).full_rows.get(event.row_key)
        if row:
            webbrowser.open(row.url)

    def _open_modal(self, screen, callback=None) -> None:
        table = self.query_one(HistoryTable)
        table.marquee.pause()

        def wrapped(result) -> None:
            self.query_one(HistoryTable).marquee.resume()
            if callback:
                callback(result)

        self.push_screen(screen, wrapped)

    def show_info(self, row: HistoryRow) -> None:
        self._open_modal(InfoScreen(row))

    def action_noop(self) -> None:
        pass


def main() -> None:
    ChromeHistoryApp().run()


if __name__ == "__main__":
    main()
