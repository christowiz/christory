"""FilterInput — Input subclass that escapes to the results table."""
from __future__ import annotations

from textual.binding import Binding
from textual.widgets import Input


class FilterInput(Input):
    BINDINGS = [
        Binding("down", "focus_table", show=False),
        Binding("escape", "focus_table", show=False),
    ]

    def action_focus_table(self) -> None:
        from .history_table import HistoryTable
        self.app.query_one(HistoryTable).focus()
