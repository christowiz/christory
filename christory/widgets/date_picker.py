"""DatePickerScreen — modal month calendar that emits date-filter strings."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from ..date_filter import DateFilter


class DatePickerScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("enter", "select", show=False),
        Binding("s", "set_start", show=False),
        Binding("e", "set_end", show=False),
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

    def __init__(
        self,
        initial: date | None = None,
        initial_start: date | None = None,
        initial_end: date | None = None,
        on_filter_change=None,
    ) -> None:
        super().__init__()
        self.selected = initial or date.today()
        self.start: date | None = initial_start
        self.end: date | None = initial_end
        self._on_filter_change = on_filter_change

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self._header_text(), id="cal-header"),
            Static(self._grid_text(), id="cal-grid"),
            Static(self._help_text(), id="cal-help"),
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
        if self.start is not None and self.end is not None:
            range_lo, range_hi = sorted([self.start, self.end])
        else:
            range_lo = range_hi = None
        lines = ["[dim]Su Mo Tu We Th Fr Sa[/dim]"]
        for week in weeks:
            cells = []
            for day in week:
                label = f"{day.day:>2}"
                is_cursor = day == self.selected
                is_start = self.start is not None and day == self.start
                is_end = self.end is not None and day == self.end
                styles: list[str] = []
                if is_cursor:
                    styles.append("reverse")
                elif is_start and is_end:
                    styles.append("b magenta")
                elif is_start:
                    styles.append("b green")
                elif is_end:
                    styles.append("b red")
                else:
                    if range_lo is not None and range_lo <= day <= range_hi:
                        styles.append("underline")
                    if day.month != m:
                        styles.append("dim")
                    elif day == today:
                        styles.append("b yellow")
                if styles:
                    style_str = " ".join(styles)
                    label = f"[{style_str}]{label}[/{style_str}]"
                cells.append(label)
            lines.append(" ".join(cells))
        return "\n".join(lines)

    def _help_text(self) -> str:
        return (
            "[b]←→ h/l[/b] day  [b]↑↓ j/k[/b] week  "
            "[b][ ][/b] month  [b]{ }[/b] year  [b]t[/b] today  "
            "[b]s[/b] start  [b]e[/b] end  [b]enter[/b] day  [b]esc[/b] close"
        )

    def _refresh_cal(self) -> None:
        self.query_one("#cal-header", Static).update(self._header_text())
        self.query_one("#cal-grid", Static).update(self._grid_text())
        self.query_one("#cal-help", Static).update(self._help_text())

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
        df = DateFilter.from_range(self.selected, self.selected)
        if self._on_filter_change is not None:
            self._on_filter_change(df.to_input_string())
        self.dismiss(None)

    def action_set_start(self) -> None:
        self.start = self.selected
        self._emit_filter()
        self._refresh_cal()

    def action_set_end(self) -> None:
        self.end = self.selected
        self._emit_filter()
        self._refresh_cal()

    def _emit_filter(self) -> None:
        if self.start is None and self.end is None:
            return
        value = DateFilter.from_range(self.start, self.end).to_input_string()
        if self._on_filter_change is not None:
            self._on_filter_change(value)
