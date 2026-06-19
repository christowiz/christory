"""Supported Chromium-based browsers and their on-disk History locations (macOS)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Browser:
    key: str
    label: str
    hotkey: str
    history_path: Path

    def installed(self) -> bool:
        return self.history_path.exists()


_APP_SUPPORT = Path.home() / "Library/Application Support"

BROWSERS: list[Browser] = [
    Browser(
        key="chrome",
        label="Google Chrome",
        hotkey="c",
        history_path=_APP_SUPPORT / "Google/Chrome/Default/History",
    ),
    Browser(
        key="brave",
        label="Brave",
        hotkey="b",
        history_path=_APP_SUPPORT / "BraveSoftware/Brave-Browser/Default/History",
    ),
    Browser(
        key="helium",
        label="Helium",
        hotkey="h",
        history_path=_APP_SUPPORT / "net.imput.helium/Default/History",
    ),
]


def get(key: str) -> Browser | None:
    for b in BROWSERS:
        if b.key == key:
            return b
    return None


def default() -> Browser:
    return BROWSERS[0]
