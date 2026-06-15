"""Central UI theme — colors, key highlights, and layout dimensions.

Concrete colors live here so the rest of the codebase references ACCENT etc.
instead of repeating values. Textual theme variables ($surface, $boost,
$text-muted) stay inline in CSS — they pick up the active theme."""

# Primary brand color (replaces Textual's default $accent blue across our UI).
ACCENT = "#fa841a"

# Help-bar key bindings render in this color instead of bold.
KEY_HIGHLIGHT = ACCENT

# Status bar error markup.
STATUS_ERROR = "red"

# DatePicker calendar cell styling (Rich markup style strings).
CAL_RANGE_BOTH = "b magenta"
CAL_RANGE_START = "b green"
CAL_RANGE_END = "b red"
CAL_TODAY = "b yellow"

# Gap between filter bar and results table (Textual rows of cells).
FILTER_RESULTS_GAP = 1
