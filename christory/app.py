"""Chrome history search TUI — app shell and entry point."""
from __future__ import annotations

import webbrowser

from rich.text import Text

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
from . import browsers
from .browsers import Browser
from .date_filter import DateFilter
from .db import HistoryDatabase, HistoryRow
from .settings import Settings
from .theme import ACCENT, STATUS_ERROR
from .widgets import (
    BrowserPickerScreen,
    DatePickerScreen,
    FilterInput,
    HistoryTable,
    InfoScreen,
)


class ChromeHistoryApp(App):
    TITLE = "Chrome History Search"
    BINDINGS = [
        Binding("ctrl+c", "quit", show=False, priority=True),
        Binding("ctrl+q", "noop", show=False, priority=True),
    ]
    CSS = APP_CSS

    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings.load()
        browser = browsers.get(self.settings.default_browser) or browsers.default()
        self.db = HistoryDatabase(browser)
        self.sub_title = browser.label
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
            status.update(f"[{STATUS_ERROR}]{e}[/]")

    def update_sort_status(self) -> None:
        table = self.query_one(HistoryTable)
        col = DISPLAY_LABELS[SORT_COLUMNS[table.sort_index]]
        arrow = SORT_DESC_ARROW if table.sort_descending else SORT_ASC_ARROW
        n = len(table.full_rows)
        parts = [
            f"browser: {self.db.browser.label}",
            f"{n} result(s)",
            f"sort: {col} {arrow}",
        ]
        group_label = self._group_status_label(table)
        if group_label:
            parts.append(f"group: {group_label}")
        parts.append(f"snapshot: {self.db.snapshot_path}")
        self.query_one("#status", Static).update("  ·  ".join(parts))

    def _group_status_label(self, table) -> str:
        date_filter = DateFilter.parse(self.query_one("#date", Input).value)
        by_day, by_hour = self._effective_grouping(table, date_filter)
        active = []
        if by_day:
            active.append("day")
        if by_hour:
            active.append("hour")
        if active:
            return "+".join(active)
        requested = []
        if table.group_day:
            requested.append("day")
        if table.group_hour:
            requested.append("hour")
        return f"{'+'.join(requested)} (n/a)" if requested else ""

    def _effective_grouping(self, table, date_filter: DateFilter) -> tuple[bool, bool]:
        single_day = date_filter.is_single_day()
        by_day = table.group_day and not single_day
        by_hour = table.group_hour
        return by_day, by_hour

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
        table.group_keys.clear()

        by_day, by_hour = self._effective_grouping(table, date_filter)
        grouped = by_day or by_hour
        show_day_in_hour_only = by_hour and not by_day and not date_filter.is_single_day()

        if grouped:
            self._populate_grouped(
                table, rows, by_day=by_day, by_hour=by_hour,
                show_day_in_hour=show_day_in_hour_only,
            )
            table.update_sort_indicators()
        else:
            for row in rows:
                self._add_data_row(table, row)
            if not (table.sort_index == 0 and table.sort_descending):
                table.apply_sort()

        self.update_sort_status()
        if table.row_count:
            first = table.first_data_row() if grouped else 0
            if first is not None:
                table.move_cursor(row=first, animate=False)
                table.attach_marquee_to_cursor()

    def _add_data_row(self, table: HistoryTable, row: HistoryRow) -> None:
        cells = [row.visited]
        if SHOW_VISITS:
            cells.append(str(row.visits))
        cells.append(row.title[: table.title_width])
        cells.append(row.url[: table.url_width])
        key = table.add_row(*cells)
        table.full_rows[key] = row

    def _add_group_row(self, table: HistoryTable, label: str) -> None:
        cells: list = ["", *(("",) if SHOW_VISITS else ()), Text(label, style=f"bold {ACCENT}"), ""]
        key = table.add_row(*cells)
        table.group_keys.add(key)

    def _populate_grouped(
        self,
        table: HistoryTable,
        rows: list[HistoryRow],
        *,
        by_day: bool,
        by_hour: bool,
        show_day_in_hour: bool,
    ) -> None:
        last_day: str | None = None
        last_hour: str | None = None
        for row in rows:
            day = row.visited[:10]
            hour = row.visited[11:13] + ":00" if len(row.visited) >= 13 else "??:00"
            if by_day and day != last_day:
                self._add_group_row(table, f"▼ {day}")
                last_day = day
                last_hour = None
            if by_hour:
                if by_day:
                    hour_key = hour
                    hour_label = f"    ▸ {hour}"
                elif show_day_in_hour:
                    hour_key = f"{day} {hour}"
                    hour_label = f"▸ {day} {hour}"
                else:
                    hour_key = hour
                    hour_label = f"▸ {hour}"
                if hour_key != last_hour:
                    self._add_group_row(table, hour_label)
                    last_hour = hour_key
            self._add_data_row(table, row)

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

    def action_pick_browser(self) -> None:
        self._open_modal(
            BrowserPickerScreen(
                current_key=self.db.browser.key,
                default_key=self.settings.default_browser,
                on_set_default=self._set_default_browser,
            ),
            callback=self._apply_browser_choice,
        )

    def _apply_browser_choice(self, browser: Browser | None) -> None:
        if browser is None or browser.key == self.db.browser.key:
            return
        self.db.set_browser(browser)
        self.sub_title = browser.label
        self.action_refresh()

    def _set_default_browser(self, browser: Browser) -> None:
        self.settings.default_browser = browser.key
        self.settings.save()

    def action_noop(self) -> None:
        pass


def main() -> None:
    ChromeHistoryApp().run()


if __name__ == "__main__":
    main()
