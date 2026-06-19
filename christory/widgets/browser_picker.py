"""BrowserPickerScreen — modal that picks a Chromium browser and (optionally) marks it default."""
from __future__ import annotations

from rich.text import Text

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from ..browsers import BROWSERS, Browser
from ..theme import ACCENT


CURRENT_MARK = "●"
DEFAULT_MARK = "★"


class BrowserPickerScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", show=False),
        Binding("enter", "select", show=False),
        Binding("up", "move(-1)", show=False),
        Binding("k", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("j", "move(1)", show=False),
        Binding("d", "mark_default", show=False),
        Binding("c", "hotkey('chrome')", show=False),
        Binding("b", "hotkey('brave')", show=False),
        Binding("h", "hotkey('helium')", show=False),
    ]

    DEFAULT_CSS = f"""
    BrowserPickerScreen {{ align: center middle; }}
    #browser-box {{
        width: 52;
        height: auto;
        padding: 1 2;
        border: round {ACCENT};
        background: $surface;
    }}
    #browser-title {{ width: 100%; text-align: center; margin-bottom: 1; }}
    #browser-list {{ width: 100%; margin-bottom: 1; }}
    #browser-help {{ width: 100%; color: $text-muted; }}
    """

    def __init__(
        self,
        current_key: str,
        default_key: str,
        on_set_default=None,
    ) -> None:
        super().__init__()
        self._current_key = current_key
        self._default_key = default_key
        self._on_set_default = on_set_default
        self._cursor = next(
            (i for i, b in enumerate(BROWSERS) if b.key == current_key), 0
        )

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("[b]Browser[/b]", id="browser-title"),
            Static(self._list_renderable(), id="browser-list"),
            Static(self._help_text(), id="browser-help"),
            id="browser-box",
        )

    def _list_renderable(self) -> Text:
        out = Text(no_wrap=True, overflow="crop")
        for i, b in enumerate(BROWSERS):
            cursor = ">" if i == self._cursor else " "
            current = CURRENT_MARK if b.key == self._current_key else " "
            default = DEFAULT_MARK if b.key == self._default_key else " "
            text = f"{cursor} [{b.hotkey}] {current}{default} {b.label}"
            if not b.installed():
                text += "  (not installed)"
            line = Text(text)
            if not b.installed():
                line.stylize("dim")
            elif i == self._cursor:
                line.stylize("reverse")
            if i:
                out.append("\n")
            out.append_text(line)
        return out

    def _help_text(self) -> str:
        return (
            f"[b]↑↓ j/k[/b] move  [b]enter[/b] select  "
            f"[b]d[/b] set default  [b]esc[/b] close\n"
            f"{CURRENT_MARK} current   {DEFAULT_MARK} default"
        )

    def _refresh(self) -> None:
        self.query_one("#browser-list", Static).update(self._list_renderable())

    def action_move(self, delta: int) -> None:
        self._cursor = (self._cursor + delta) % len(BROWSERS)
        self._refresh()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_select(self) -> None:
        self.dismiss(BROWSERS[self._cursor])

    def action_hotkey(self, key: str) -> None:
        for i, b in enumerate(BROWSERS):
            if b.key == key:
                self._cursor = i
                self.dismiss(b)
                return

    def action_mark_default(self) -> None:
        browser = BROWSERS[self._cursor]
        self._default_key = browser.key
        if self._on_set_default is not None:
            self._on_set_default(browser)
        self._refresh()
        self.app.notify(f"Default browser: {browser.label}")
