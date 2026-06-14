"""Chrome history search TUI."""
from __future__ import annotations

import calendar
import shutil
import sqlite3
import subprocess
import tempfile
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path

from rich.text import Text

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import DataTable, Header, Input, Static


CHROME_HISTORY = Path.home() / "Library/Application Support/Google/Chrome/Default/History"
WEBKIT_EPOCH_OFFSET = 11_644_473_600

# Flip to True to bring the Visits column back into the main table.
SHOW_VISITS = False

VISITED_WIDTH = 16
VISITS_WIDTH = 7
MIN_TEXT_WIDTH = 20

MARQUEE_DELAY = 1.0
MARQUEE_INTERVAL = 0.25
ROW_LIMIT = 10_000


def _build_sort_columns() -> list[str]:
    cols = ["visited"]
    if SHOW_VISITS:
        cols.append("visits")
    cols.extend(["title", "url"])
    return cols


SORT_COLUMNS = _build_sort_columns()
SORT_DEFAULT_DESC = {"visited": True, "visits": True, "title": False, "url": False}
DISPLAY_LABELS = {"visited": "Date", "visits": "Visits", "title": "Title", "url": "URL"}
SORT_DESC_ARROW = "▼"
SORT_ASC_ARROW = "▲"


HELP_TEXT = (
    "[b]General[/b]    : "
    "[b]q[/b] / [b]ctrl-c[/b]: quit  [b]r[/b]: refresh  [b]tab[/b]: switch focus  "
    "[b]/[/b]: focus search  [b]enter[/b]: focus table / open url  "
    "[b]↓[/b] / [b]esc[/b]: from filter → table  [b]s/S[/b]: sort col / dir\n"
    "[b]Filter[/b]     : "
    "[b]search[/b]: URL + title  [b]domain[/b]: URL only  "
    "[b]date[/b]: prefix e.g. 2026-05-20 — or [b]enter[/b] for calendar\n"
    "[b]Navigation[/b] : "
    "[b]j[/b]/[b]↓[/b]: down  [b]k[/b]/[b]↑[/b]: up  "
    "[b]PageUp[/b] / [b]Ctrl-U[/b]: page up  "
    "[b]PageDown[/b] / [b]Ctrl-D[/b]: page down  "
    "[b]g[/b]: top  [b]G[/b]: bottom\n"
    "[b]Commands[/b]   : "
    "[b]i[/b]: info  [b]c[/b]: copy URL  [b]a[/b]: copy all  "
    "[b]enter[/b]: open URL  [b]esc[/b]: dismiss modal"
)


def copy_history_db() -> Path:
    if not CHROME_HISTORY.exists():
        raise FileNotFoundError(f"Chrome history not found at {CHROME_HISTORY}")
    tmp = Path(tempfile.gettempdir()) / "chrome_history_tui.db"
    shutil.copyfile(CHROME_HISTORY, tmp)
    return tmp


def webkit_to_local(webkit_us: int) -> str:
    if not webkit_us:
        return ""
    return datetime.fromtimestamp(webkit_us / 1_000_000 - WEBKIT_EPOCH_OFFSET).strftime(
        "%Y-%m-%d %H:%M"
    )


def search_history(db, text, domain, date_prefix, limit=ROW_LIMIT):
    text_like = f"%{text}%"
    domain_like = f"%{domain}%"
    date_like = f"{date_prefix}%"
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        return conn.execute(
            """
            SELECT last_visit_time, visit_count, COALESCE(title, ''), url
            FROM urls
            WHERE (url LIKE :text OR title LIKE :text)
              AND url LIKE :domain
              AND strftime('%Y-%m-%d %H:%M', last_visit_time/1000000 - 11644473600, 'unixepoch', 'localtime') LIKE :date
            ORDER BY last_visit_time DESC
            LIMIT :limit
            """,
            {"text": text_like, "domain": domain_like, "date": date_like, "limit": limit},
        ).fetchall()


def marquee_slice(text: str, width: int, offset: int) -> str:
    if len(text) <= width:
        return text
    padded = text + "   "
    o = offset % len(padded)
    return (padded + padded)[o : o + width]


def format_info(row: dict) -> str:
    return (
        f"Title: {row['title']}\n"
        f"URL: {row['url']}\n"
        f"Visited: {row['visited']}\n"
        f"Visits: {row['visits']}"
    )


def copy_text_to_clipboard(app: App, text: str) -> None:
    """Use Textual's OSC52 copy if available; fall back to pbcopy on macOS."""
    copied = False
    try:
        app.copy_to_clipboard(text)
        copied = True
    except Exception:
        pass
    if not copied:
        try:
            subprocess.run(["pbcopy"], input=text.encode(), check=False)
        except FileNotFoundError:
            pass


class FilterInput(Input):
    BINDINGS = [
        Binding("down", "focus_table", show=False),
        Binding("escape", "focus_table", show=False),
    ]

    def action_focus_table(self) -> None:
        self.app.query_one(HistoryTable).focus()


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


class DatePickerScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("enter", "select", show=False),
        Binding("left", "move(-1,0,0)", show=False),
        Binding("h", "move(-1,0,0)", show=False),
        Binding("right", "move(1,0,0)", show=False),
        Binding("l", "move(1,0,0)", show=False),
        Binding("up", "move(-7,0,0)", show=False),
        Binding("k", "move(-7,0,0)", show=False),
        Binding("down", "move(7,0,0)", show=False),
        Binding("j", "move(7,0,0)", show=False),
        Binding("[", "move(0,-1,0)", show=False),
        Binding("]", "move(0,1,0)", show=False),
        Binding("{", "move(0,0,-1)", show=False),
        Binding("}", "move(0,0,1)", show=False),
        Binding("t", "today", show=False),
    ]

    DEFAULT_CSS = """
    DatePickerScreen { align: center middle; }
    #cal-box {
        width: 32;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }
    #cal-header { width: 100%; text-align: center; margin-bottom: 1; }
    #cal-grid { width: 100%; margin-bottom: 1; }
    #cal-help { width: 100%; color: $text-muted; }
    """

    def __init__(self, initial: date | None = None) -> None:
        super().__init__()
        self.selected = initial or date.today()

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self._header_text(), id="cal-header"),
            Static(self._grid_text(), id="cal-grid"),
            Static(
                "[b]←→ h/l[/b] day  [b]↑↓ j/k[/b] week  "
                "[b][ ][/b] month  [b]{ }[/b] year  "
                "[b]t[/b] today  [b]enter[/b] pick  [b]esc[/b] cancel",
                id="cal-help",
            ),
            id="cal-box",
        )

    def on_mount(self) -> None:
        self._refresh_cal()

    def _header_text(self) -> str:
        return f"[b]{self.selected.strftime('%B %Y')}[/b]"

    def _grid_text(self) -> str:
        y, m = self.selected.year, self.selected.month
        weeks = calendar.Calendar(firstweekday=6).monthdatescalendar(y, m)
        today = date.today()
        lines = ["[dim]Su Mo Tu We Th Fr Sa[/dim]"]
        for week in weeks:
            cells = []
            for day in week:
                label = f"{day.day:>2}"
                if day == self.selected:
                    label = f"[reverse]{label}[/reverse]"
                elif day.month != m:
                    label = f"[dim]{label}[/dim]"
                elif day == today:
                    label = f"[b yellow]{label}[/b yellow]"
                cells.append(label)
            lines.append(" ".join(cells))
        return "\n".join(lines)

    def _refresh_cal(self) -> None:
        self.query_one("#cal-header", Static).update(self._header_text())
        self.query_one("#cal-grid", Static).update(self._grid_text())

    def action_move(self, days: int, months: int, years: int) -> None:
        new = self.selected
        if days:
            new = new + timedelta(days=days)
        if months or years:
            new_y = new.year + years
            new_m = new.month + months
            while new_m > 12:
                new_m -= 12
                new_y += 1
            while new_m < 1:
                new_m += 12
                new_y -= 1
            last_day = calendar.monthrange(new_y, new_m)[1]
            new = new.replace(year=new_y, month=new_m, day=min(new.day, last_day))
        self.selected = new
        self._refresh_cal()

    def action_today(self) -> None:
        self.selected = date.today()
        self._refresh_cal()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        self.dismiss(self.selected.strftime("%Y-%m-%d"))


class InfoScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("c", "copy_url", "Copy URL"),
        Binding("a", "copy_all", "Copy all"),
    ]

    DEFAULT_CSS = """
    InfoScreen { align: center middle; }
    #info-box {
        width: 80%;
        max-width: 110;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }
    #info-box Static { margin-bottom: 1; }
    """

    def __init__(self, row: dict) -> None:
        super().__init__()
        self.row = row

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[b]Visited[/b]  {self.row['visited']}    [b]Visits[/b]  {self.row['visits']}"),
            Static(f"[b]Title[/b]\n{self.row['title'] or '(no title)'}"),
            Static(f"[b]URL[/b]\n{self.row['url']}"),
            Static("[dim]esc: close   c: copy URL   a: copy all[/dim]"),
            id="info-box",
        )

    def action_copy_url(self) -> None:
        copy_text_to_clipboard(self.app, self.row["url"])
        self.app.notify("URL copied")

    def action_copy_all(self) -> None:
        copy_text_to_clipboard(self.app, format_info(self.row))
        self.app.notify("Info copied")


class HistoryTable(DataTable):
    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("g", "goto_top", show=False),
        Binding("G", "goto_bottom", show=False),
        Binding("ctrl+d", "cursor_page_down", show=False),
        Binding("ctrl+u", "cursor_page_up", show=False),
        Binding("pageup", "cursor_page_up", show=False),
        Binding("pagedown", "cursor_page_down", show=False),
        Binding("s", "sort_next", show=False),
        Binding("S", "sort_reverse", show=False),
        Binding("i", "show_info", show=False),
        Binding("c", "copy_url", show=False),
        Binding("a", "copy_all", show=False),
        Binding("r", "refresh_db", show=False),
        Binding("q", "quit_app", show=False),
        Binding("slash", "focus_search", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.full_rows: dict = {}
        self.col_keys: dict = {}
        self.title_width = 30
        self.url_width = 50
        self.sort_index = 0
        self.sort_descending = SORT_DEFAULT_DESC[SORT_COLUMNS[0]]
        self._marquee_delay_timer = None
        self._marquee_timer = None
        self._marquee_offset = 0
        self._marquee_row_key = None
        self._marquee_paused = False

    def action_goto_top(self) -> None:
        if self.row_count:
            self.move_cursor(row=0, animate=False)

    def action_goto_bottom(self) -> None:
        if self.row_count:
            self.move_cursor(row=self.row_count - 1, animate=False)

    def _page_size(self) -> int:
        # Visible rows = viewport height minus the header row.
        return max(1, self.size.height - 1)

    def action_cursor_page_down(self) -> None:
        if not self.row_count:
            return
        new_row = min(self.cursor_row + self._page_size(), self.row_count - 1)
        self.move_cursor(row=new_row, animate=False)

    def action_cursor_page_up(self) -> None:
        if not self.row_count:
            return
        new_row = max(self.cursor_row - self._page_size(), 0)
        self.move_cursor(row=new_row, animate=False)

    def action_sort_next(self) -> None:
        self.sort_index = (self.sort_index + 1) % len(SORT_COLUMNS)
        self.sort_descending = SORT_DEFAULT_DESC[SORT_COLUMNS[self.sort_index]]
        self.apply_sort()

    def action_sort_reverse(self) -> None:
        self.sort_descending = not self.sort_descending
        self.apply_sort()

    def apply_sort(self) -> None:
        self._stop_marquee()
        col_key = self.col_keys[SORT_COLUMNS[self.sort_index]]
        self.sort(col_key, reverse=self.sort_descending)
        self.update_sort_indicators()
        self.app.update_sort_status()
        self._restart_marquee()

    def update_sort_indicators(self) -> None:
        active = SORT_COLUMNS[self.sort_index]
        arrow = SORT_DESC_ARROW if self.sort_descending else SORT_ASC_ARROW
        for name, col_key in self.col_keys.items():
            col = self.columns.get(col_key)
            if col is None:
                continue
            base = DISPLAY_LABELS.get(name, name.title())
            label = f"{base} {arrow}" if name == active else base
            try:
                col.label = Text.from_markup(label)
            except Exception:
                try:
                    col.label = label
                except Exception:
                    pass
        try:
            self._require_update_dimensions = True
        except AttributeError:
            pass
        self.refresh(layout=True)

    def action_show_info(self) -> None:
        row = self._row_for_cursor()
        if row:
            self.app.show_info(row)

    def action_copy_url(self) -> None:
        row = self._row_for_cursor()
        if row:
            copy_text_to_clipboard(self.app, row["url"])
            self.app.notify("URL copied")

    def action_copy_all(self) -> None:
        row = self._row_for_cursor()
        if row:
            copy_text_to_clipboard(self.app, format_info(row))
            self.app.notify("Info copied")

    def action_refresh_db(self) -> None:
        self.app.action_refresh()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_focus_search(self) -> None:
        self.app.query_one("#search", Input).focus()

    @on(DataTable.RowHighlighted)
    def _row_highlighted(self) -> None:
        self._restart_marquee()

    def _row_for_cursor(self) -> dict | None:
        if self.cursor_row < 0 or self.cursor_row >= self.row_count:
            return None
        try:
            row_key = self.coordinate_to_cell_key(Coordinate(self.cursor_row, 0)).row_key
        except Exception:
            return None
        return self.full_rows.get(row_key)

    def _current_row_key(self):
        try:
            return self.coordinate_to_cell_key(Coordinate(self.cursor_row, 0)).row_key
        except Exception:
            return None

    def _restart_marquee(self) -> None:
        self._stop_marquee()
        if self._marquee_paused:
            return
        row_key = self._current_row_key()
        if row_key is None:
            return
        row = self.full_rows.get(row_key)
        if not row:
            return
        if len(row["title"]) <= self.title_width and len(row["url"]) <= self.url_width:
            return
        self._marquee_offset = 0
        self._marquee_row_key = row_key
        self._marquee_delay_timer = self.set_timer(MARQUEE_DELAY, self._start_marquee)

    def _start_marquee(self) -> None:
        if self._marquee_paused or self._marquee_row_key is None:
            return
        self._marquee_timer = self.set_interval(MARQUEE_INTERVAL, self._tick_marquee)

    def _tick_marquee(self) -> None:
        if self._marquee_paused or self._marquee_row_key is None:
            return
        row = self.full_rows.get(self._marquee_row_key)
        if not row:
            return
        self._marquee_offset += 1
        try:
            self.update_cell(
                self._marquee_row_key,
                self.col_keys["title"],
                marquee_slice(row["title"], self.title_width, self._marquee_offset),
            )
            self.update_cell(
                self._marquee_row_key,
                self.col_keys["url"],
                marquee_slice(row["url"], self.url_width, self._marquee_offset),
            )
        except Exception:
            pass

    def _stop_marquee(self) -> None:
        if self._marquee_delay_timer:
            self._marquee_delay_timer.stop()
            self._marquee_delay_timer = None
        if self._marquee_timer:
            self._marquee_timer.stop()
            self._marquee_timer = None
        if self._marquee_row_key is not None:
            row = self.full_rows.get(self._marquee_row_key)
            if row:
                try:
                    self.update_cell(
                        self._marquee_row_key,
                        self.col_keys["title"],
                        row["title"][:self.title_width],
                    )
                    self.update_cell(
                        self._marquee_row_key,
                        self.col_keys["url"],
                        row["url"][:self.url_width],
                    )
                except Exception:
                    pass
        self._marquee_row_key = None

    def pause_marquee(self) -> None:
        self._marquee_paused = True
        self._stop_marquee()

    def resume_marquee(self) -> None:
        self._marquee_paused = False
        self._restart_marquee()

    def set_text_widths(self, title_w: int, url_w: int) -> None:
        if title_w == self.title_width and url_w == self.url_width:
            return
        self.title_width = title_w
        self.url_width = url_w
        for name, w in (("title", title_w), ("url", url_w)):
            col_key = self.col_keys.get(name)
            col = self.columns.get(col_key) if col_key else None
            if col is None:
                continue
            try:
                col.width = w
            except Exception:
                pass
            for attr in ("content_width", "render_width"):
                if hasattr(col, attr):
                    try:
                        setattr(col, attr, w)
                    except Exception:
                        pass
            if hasattr(col, "auto_width"):
                try:
                    col.auto_width = False
                except Exception:
                    pass
        self._stop_marquee()
        for i, (row_key, full) in enumerate(self.full_rows.items()):
            try:
                self.update_cell(
                    row_key,
                    self.col_keys["title"],
                    full["title"][:title_w],
                    update_width=(i == 0),
                )
                self.update_cell(
                    row_key,
                    self.col_keys["url"],
                    full["url"][:url_w],
                    update_width=(i == 0),
                )
            except Exception:
                pass
        try:
            self._clear_caches()
        except AttributeError:
            pass
        self.refresh(layout=True)
        self._restart_marquee()


class ChromeHistoryApp(App):
    TITLE = "Chrome History Search"
    BINDINGS = [
        Binding("ctrl+c", "quit", show=False, priority=True),
        Binding("ctrl+q", "noop", show=False, priority=True),
    ]
    CSS = """
    #filter-bar { height: 3; padding: 0 2; }
    #filter-bar Input { width: 1fr; margin-right: 1; }
    #filter-bar Input:last-of-type { margin-right: 0; }
    #status { padding: 0 2; height: 1; color: $text-muted; }
    DataTable { height: 1fr; margin: 0 2; }
    #help { background: $boost; padding: 0 2; color: $text-muted; height: auto; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.db_path: Path | None = None
        self._resize_debounce = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Horizontal(
            FilterInput(placeholder="search text…  (/ to focus)", id="search"),
            FilterInput(placeholder="domain…  e.g. github.com", id="domain"),
            FilterInput(placeholder="date…  e.g. 2026-05-20 or Enter for calendar", id="date"),
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
            self.db_path = copy_history_db()
            self.run_search()
        except FileNotFoundError as e:
            status.update(f"[red]{e}[/red]")

    def update_sort_status(self) -> None:
        table = self.query_one(HistoryTable)
        col = DISPLAY_LABELS[SORT_COLUMNS[table.sort_index]]
        arrow = SORT_DESC_ARROW if table.sort_descending else SORT_ASC_ARROW
        n = table.row_count
        self.query_one("#status", Static).update(
            f"{n} result(s)  ·  sort: {col} {arrow}  ·  snapshot: {self.db_path}"
        )

    def run_search(self) -> None:
        if not self.db_path:
            return
        text = self.query_one("#search", Input).value.strip()
        domain = self.query_one("#domain", Input).value.strip()
        date = self.query_one("#date", Input).value.strip()
        rows = search_history(self.db_path, text, domain, date)
        table = self.query_one(HistoryTable)
        table._stop_marquee()
        table.clear()
        table.full_rows.clear()
        for ts, count, title, url in rows:
            visited = webkit_to_local(ts)
            cells = [visited]
            if SHOW_VISITS:
                cells.append(str(count))
            cells.append(title[: table.title_width])
            cells.append(url[: table.url_width])
            key = table.add_row(*cells)
            table.full_rows[key] = {
                "visited": visited,
                "visits": count,
                "title": title,
                "url": url,
            }
        if not (table.sort_index == 0 and table.sort_descending):
            table.apply_sort()
        self.update_sort_status()
        if table.row_count:
            table.move_cursor(row=0, animate=False)
            table._restart_marquee()

    @on(Input.Changed)
    def _filter_changed(self, event: Input.Changed) -> None:
        self.run_search()

    @on(Input.Submitted)
    def _input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "date":
            self._open_modal(
                DatePickerScreen(_parse_date_input(event.value)),
                self._date_picked,
            )
        else:
            self.query_one(HistoryTable).focus()

    def _date_picked(self, picked) -> None:
        if picked:
            date_input = self.query_one("#date", Input)
            date_input.value = picked

    @on(DataTable.RowSelected)
    def _row_selected(self, event: DataTable.RowSelected) -> None:
        row = self.query_one(HistoryTable).full_rows.get(event.row_key)
        if row:
            webbrowser.open(row["url"])

    def _open_modal(self, screen, callback=None) -> None:
        self.query_one(HistoryTable).pause_marquee()

        def wrapped(result) -> None:
            self.query_one(HistoryTable).resume_marquee()
            if callback:
                callback(result)

        self.push_screen(screen, wrapped)

    def show_info(self, row: dict) -> None:
        self._open_modal(InfoScreen(row))

    def action_noop(self) -> None:
        pass


def main() -> None:
    ChromeHistoryApp().run()


if __name__ == "__main__":
    main()
