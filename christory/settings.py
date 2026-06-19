"""Persistent user settings — JSON file under ~/.config/christory/."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

SETTINGS_PATH = Path.home() / ".config/christory/settings.json"


@dataclass
class Settings:
    default_browser: str = "chrome"

    @classmethod
    def load(cls) -> "Settings":
        try:
            data = json.loads(SETTINGS_PATH.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return cls()
        return cls(default_browser=str(data.get("default_browser", cls.default_browser)))

    def save(self) -> None:
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(asdict(self), indent=2))
        except OSError:
            pass
