"""UI constants, sort metadata, help text, and CSS."""

# Flip to True to bring the Visits column back into the main table.
SHOW_VISITS = False

VISITED_WIDTH = 16
VISITS_WIDTH = 7
MIN_TEXT_WIDTH = 20

MARQUEE_DELAY = 1.0
MARQUEE_INTERVAL = 0.25


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
    "[b]date[/b]: prefix or range [b]A..B[/b] / [b]A..[/b] / [b]..B[/b] — or [b]enter[/b] for calendar\n"
    "[b]Navigation[/b] : "
    "[b]j[/b]/[b]↓[/b]: down  [b]k[/b]/[b]↑[/b]: up  "
    "[b]PageUp[/b] / [b]Ctrl-U[/b]: page up  "
    "[b]PageDown[/b] / [b]Ctrl-D[/b]: page down  "
    "[b]g[/b]: top  [b]G[/b]: bottom\n"
    "[b]Commands[/b]   : "
    "[b]i[/b]: info  [b]c[/b]: copy URL  [b]a[/b]: copy all  "
    "[b]enter[/b]: open URL  [b]esc[/b]: dismiss modal"
)


APP_CSS = """
#filter-bar { height: 3; padding: 0 2; }
#filter-bar Input { width: 1fr; margin-right: 1; }
#filter-bar Input:last-of-type { margin-right: 0; }
#status { padding: 0 2; height: 1; color: $text-muted; }
DataTable { height: 1fr; margin: 0 2; }
#help { background: $boost; padding: 0 2; color: $text-muted; height: auto; }
"""
