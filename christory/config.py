"""UI constants, sort metadata, help text, and CSS."""

from .theme import ACCENT, FILTER_RESULTS_GAP, KEY_HIGHLIGHT

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


_K = KEY_HIGHLIGHT
HELP_TEXT = (
    f"[{_K}]Filter[/]  : "
    f"[{_K}]/[/]: focus search   "
    f"[{_K}]tab[/]: next field   "
    f"[{_K}]↓[/]/[{_K}]esc[/]: leave filter   "
    f"[{_K}]enter[/] on date\n"
    # f"[{_K}]Calendar[/]: "
    f"[{_K}]Move[/]    : "
    f"[{_K}]j[/]/[{_K}]↓[/] down   "
    f"[{_K}]k[/]/[{_K}]↑[/]: up   "
    f"[{_K}]PgUp[/]/[{_K}]Ctrl-U[/] prev page   "
    f"[{_K}]PgDn[/]/[{_K}]Ctrl-D[/]: next page   "
    f"[{_K}]g[/]: go to top   "
    f"[{_K}]G[/]: got to bottom\n"
    f"[{_K}]Row[/]     : "
    f"[{_K}]enter[/]: open URL   "
    f"[{_K}]i[/]: info   "
    f"[{_K}]c[/]: copy URL   "
    f"[{_K}]a[/]: copy all\n"
    f"[{_K}]View[/]    : "
    f"[{_K}]s[/]/[{_K}]S[/]: sort col / dir   "
    f"[{_K}]d[/]: group by day   "
    f"[{_K}]h[/]: group by hour   "
    f"[{_K}]r[/]: refresh   "
    f"[{_K}]b[/]: browser   "
    f"[{_K}]q[/] or [{_K}]Ctrl-C[/]: quit   "
    f"[{_K}]esc[/]: close modal\n\n"
    f"(date syntax: [{_K}]YYYY[-MM[-DD]][/]  ·  [{_K}]A..B[/] / [{_K}]A..[/] / [{_K}]..B[/])\n"
)


APP_CSS = f"""
#filter-bar {{
    height: 3;
    padding: 0 2;
    margin-bottom: {FILTER_RESULTS_GAP};
}}
#filter-bar Input {{ width: 1fr; margin-right: 1; }}
#filter-bar Input:focus {{ border: tall {ACCENT}; }}
#filter-bar Input:last-of-type {{ margin-right: 0; }}
#status {{ padding: 0 2; height: 1; color: $text-muted; }}
DataTable {{ height: 1fr; margin: 0 2; }}
DataTable > .datatable--cursor {{ background: {ACCENT}; color: $text; }}
DataTable > .datatable--header {{ color: {ACCENT}; }}
#help {{ background: $boost; padding: 0 2; color: $text-muted; height: auto; }}
"""
