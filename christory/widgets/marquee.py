"""Marquee — scrolls long title/url text for one DataTable row at a time."""
from __future__ import annotations

from typing import Callable


def marquee_slice(text: str, width: int, offset: int) -> str:
    if len(text) <= width:
        return text
    padded = text + "   "
    o = offset % len(padded)
    return (padded + padded)[o : o + width]


class Marquee:
    """Owns the delay/tick timers and the scroll offset for the focused row.

    Render and re-attach are host-supplied callbacks so the marquee never reaches
    into widget internals."""

    def __init__(
        self,
        host,
        *,
        delay: float,
        interval: float,
        on_render: Callable[[object, str, str], None],
        on_resume: Callable[[], None] | None = None,
    ) -> None:
        self._host = host
        self._delay = delay
        self._interval = interval
        self._on_render = on_render
        self._on_resume = on_resume
        self._delay_timer = None
        self._timer = None
        self._offset = 0
        self._row_key = None
        self._paused = False
        self._title = ""
        self._url = ""
        self._title_width = 0
        self._url_width = 0

    @property
    def row_key(self):
        return self._row_key

    @property
    def is_paused(self) -> bool:
        return self._paused

    def attach(
        self,
        row_key,
        title: str,
        url: str,
        *,
        title_width: int,
        url_width: int,
    ) -> None:
        """Start scrolling row_key. No-op while paused or when text already fits."""
        self.detach()
        if self._paused or row_key is None:
            return
        if len(title) <= title_width and len(url) <= url_width:
            return
        self._row_key = row_key
        self._title = title
        self._url = url
        self._title_width = title_width
        self._url_width = url_width
        self._offset = 0
        self._delay_timer = self._host.set_timer(self._delay, self._start)

    def detach(self) -> None:
        """Stop scrolling and restore the row's cells to truncated baseline."""
        if self._delay_timer:
            self._delay_timer.stop()
            self._delay_timer = None
        if self._timer:
            self._timer.stop()
            self._timer = None
        if self._row_key is not None:
            self._on_render(
                self._row_key,
                self._title[: self._title_width],
                self._url[: self._url_width],
            )
        self._row_key = None

    def pause(self) -> None:
        self._paused = True
        self.detach()

    def resume(self) -> None:
        if not self._paused:
            return
        self._paused = False
        if self._on_resume is not None:
            self._on_resume()

    def _start(self) -> None:
        if self._paused or self._row_key is None:
            return
        self._timer = self._host.set_interval(self._interval, self._tick)

    def _tick(self) -> None:
        if self._paused or self._row_key is None:
            return
        self._offset += 1
        self._on_render(
            self._row_key,
            marquee_slice(self._title, self._title_width, self._offset),
            marquee_slice(self._url, self._url_width, self._offset),
        )
