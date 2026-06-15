"""Clipboard copy: Textual OSC52 with pbcopy fallback."""
from __future__ import annotations

import subprocess

from textual.app import App


def copy_text_to_clipboard(app: App, text: str) -> None:
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
