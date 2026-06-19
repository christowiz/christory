"""HistoryTable — DataTable with sort cycling, marquee scrolling, and row actions."""
from __future__ import annotations

from rich.text import Text

from textual import on
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Input

from ..clipboard import copy_text_to_clipboard
from ..config import (
    DISPLAY_LABELS,
    MARQUEE_DELAY,
    MARQUEE_INTERVAL,
    SORT_ASC_ARROW,
    SORT_COLUMNS,
    SORT_DEFAULT_DESC,
    SORT_DESC_ARROW,
)
from ..db import HistoryRow
from .marquee import Marquee


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
        Binding("d", "toggle_group_day", show=False),
        Binding("h", "toggle_group_hour", show=False),
        Binding("i", "show_info", show=False),
        Binding("c", "copy_url", show=False),
        Binding("a", "copy_all", show=False),
        Binding("r", "refresh_db", show=False),
        Binding("b", "pick_browser", show=False),
        Binding("q", "quit_app", show=False),
        Binding("slash", "focus_search", show=False),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.full_rows: dict[object, HistoryRow] = {}
        self.group_keys: set = set()
        self.col_keys: dict = {}
        self.title_width = 30
        self.url_width = 50
        self.sort_index = 0
        self.sort_descending = SORT_DEFAULT_DESC[SORT_COLUMNS[0]]
        self.group_day = False
        self.group_hour = False
        self.marquee = Marquee(
            host=self,
            delay=MARQUEE_DELAY,
            interval=MARQUEE_INTERVAL,
            on_render=self._render_marquee_cells,
            on_resume=self.attach_marquee_to_cursor,
        )

    def _is_group_row(self, row_index: int) -> bool:
        if row_index < 0 or row_index >= self.row_count:
            return False
        try:
            key = self.coordinate_to_cell_key(Coordinate(row_index, 0)).row_key
        except Exception:
            return False
        return key in self.group_keys

    def _skip_groups(self, row_index: int, step: int) -> int | None:
        n = self.row_count
        if not n:
            return None
        i = max(0, min(n - 1, row_index))
        while 0 <= i < n and self._is_group_row(i):
            i += step
        if 0 <= i < n:
            return i
        opposite = -step
        i = max(0, min(n - 1, row_index))
        while 0 <= i < n and self._is_group_row(i):
            i += opposite
        return i if 0 <= i < n else None

    def first_data_row(self) -> int | None:
        return self._skip_groups(0, 1)

    def last_data_row(self) -> int | None:
        return self._skip_groups(self.row_count - 1, -1)

    def action_goto_top(self) -> None:
        target = self.first_data_row()
        if target is not None:
            self.move_cursor(row=target, animate=False)

    def action_goto_bottom(self) -> None:
        target = self.last_data_row()
        if target is not None:
            self.move_cursor(row=target, animate=False)

    def _page_size(self) -> int:
        return max(1, self.size.height - 1)

    def action_cursor_down(self) -> None:
        if not self.row_count:
            return
        target = self._skip_groups(self.cursor_row + 1, 1)
        if target is not None:
            self.move_cursor(row=target, animate=False)

    def action_cursor_up(self) -> None:
        if not self.row_count:
            return
        target = self._skip_groups(self.cursor_row - 1, -1)
        if target is not None:
            self.move_cursor(row=target, animate=False)

    def action_cursor_page_down(self) -> None:
        if not self.row_count:
            return
        candidate = min(self.cursor_row + self._page_size(), self.row_count - 1)
        target = self._skip_groups(candidate, 1)
        if target is not None:
            self.move_cursor(row=target, animate=False)

    def action_cursor_page_up(self) -> None:
        if not self.row_count:
            return
        candidate = max(self.cursor_row - self._page_size(), 0)
        target = self._skip_groups(candidate, -1)
        if target is not None:
            self.move_cursor(row=target, animate=False)

    def action_sort_next(self) -> None:
        self.sort_index = (self.sort_index + 1) % len(SORT_COLUMNS)
        self.sort_descending = SORT_DEFAULT_DESC[SORT_COLUMNS[self.sort_index]]
        if self.group_day or self.group_hour:
            self.group_day = False
            self.group_hour = False
            self.app.run_search()
        else:
            self.apply_sort()

    def action_sort_reverse(self) -> None:
        self.sort_descending = not self.sort_descending
        if self.group_day or self.group_hour:
            self.group_day = False
            self.group_hour = False
            self.app.run_search()
        else:
            self.apply_sort()

    def action_toggle_group_day(self) -> None:
        self.group_day = not self.group_day
        if self.group_day:
            self.sort_index = 0
            self.sort_descending = SORT_DEFAULT_DESC[SORT_COLUMNS[0]]
        self.app.run_search()

    def action_toggle_group_hour(self) -> None:
        self.group_hour = not self.group_hour
        if self.group_hour:
            self.sort_index = 0
            self.sort_descending = SORT_DEFAULT_DESC[SORT_COLUMNS[0]]
        self.app.run_search()

    def apply_sort(self) -> None:
        self.marquee.detach()
        col_key = self.col_keys[SORT_COLUMNS[self.sort_index]]
        self.sort(col_key, reverse=self.sort_descending)
        self.update_sort_indicators()
        self.app.update_sort_status()
        self.attach_marquee_to_cursor()

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
            copy_text_to_clipboard(self.app, row.url)
            self.app.notify("URL copied")

    def action_copy_all(self) -> None:
        row = self._row_for_cursor()
        if row:
            copy_text_to_clipboard(self.app, row.format_info())
            self.app.notify("Info copied")

    def action_refresh_db(self) -> None:
        self.app.action_refresh()

    def action_pick_browser(self) -> None:
        self.app.action_pick_browser()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_focus_search(self) -> None:
        self.app.query_one("#search", Input).focus()

    @on(DataTable.RowHighlighted)
    def _row_highlighted(self) -> None:
        self.attach_marquee_to_cursor()

    def _row_for_cursor(self) -> HistoryRow | None:
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

    def attach_marquee_to_cursor(self) -> None:
        """Resolve the cursor row and hand it to the marquee."""
        row_key = self._current_row_key()
        if row_key is None:
            return
        row = self.full_rows.get(row_key)
        if row is None:
            return
        self.marquee.attach(
            row_key,
            row.title,
            row.url,
            title_width=self.title_width,
            url_width=self.url_width,
        )

    def _render_marquee_cells(self, row_key, title_slice: str, url_slice: str) -> None:
        try:
            self.update_cell(row_key, self.col_keys["title"], title_slice)
            self.update_cell(row_key, self.col_keys["url"], url_slice)
        except Exception:
            pass

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
        self.marquee.detach()
        for i, (row_key, full) in enumerate(self.full_rows.items()):
            try:
                self.update_cell(
                    row_key,
                    self.col_keys["title"],
                    full.title[:title_w],
                    update_width=(i == 0),
                )
                self.update_cell(
                    row_key,
                    self.col_keys["url"],
                    full.url[:url_w],
                    update_width=(i == 0),
                )
            except Exception:
                pass
        try:
            self._clear_caches()
        except AttributeError:
            pass
        self.refresh(layout=True)
        self.attach_marquee_to_cursor()
