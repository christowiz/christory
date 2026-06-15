"""InfoScreen — modal detail panel for a single history row."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from ..clipboard import copy_text_to_clipboard
from ..db import HistoryRow
from ..theme import ACCENT


class InfoScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("c", "copy_url", "Copy URL"),
        Binding("a", "copy_all", "Copy all"),
    ]

    DEFAULT_CSS = f"""
    InfoScreen {{ align: center middle; }}
    #info-box {{
        width: 80%;
        max-width: 110;
        height: auto;
        padding: 1 2;
        border: round {ACCENT};
        background: $surface;
    }}
    #info-box Static {{ margin-bottom: 1; }}
    """

    def __init__(self, row: HistoryRow) -> None:
        super().__init__()
        self.row = row

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[b]Visited[/b]  {self.row.visited}    [b]Visits[/b]  {self.row.visits}"),
            Static(f"[b]Title[/b]\n{self.row.title or '(no title)'}"),
            Static(f"[b]URL[/b]\n{self.row.url}"),
            Static("[dim]esc: close   c: copy URL   a: copy all[/dim]"),
            id="info-box",
        )

    def action_copy_url(self) -> None:
        copy_text_to_clipboard(self.app, self.row.url)
        self.app.notify("URL copied")

    def action_copy_all(self) -> None:
        copy_text_to_clipboard(self.app, self.row.format_info())
        self.app.notify("Info copied")
