# christory

A terminal UI for searching local Chromium-based browser history by text, domain, and date.

I got annoyed by the inabilty to filter my browsing history to find things so I created this utility for quick filtering.

Reads the `History` SQLite from any supported Chromium browser (read-only, via a temp snapshot) and renders results in a sortable table with marquee-scrolling rows, a calendar date picker, and OSC52 clipboard support.

Supported browsers: **Google Chrome**, **Brave**, **Helium**. Press `b` to switch — your active search/domain/date filters carry over.

## Requirements

- macOS (browser history paths are macOS-specific; trivial to port)
- At least one supported Chromium browser installed (Chrome, Brave, or Helium), with visits in its `Default` profile
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (recommended) for install / dev workflows

## Install

Install as an isolated tool — places a real `christory` executable on your `PATH`:

```sh
uv tool install git+https://github.com/<owner>/<repo>.git#subdirectory=christory
```

Or from a local clone:

```sh
git clone https://github.com/<owner>/<repo>.git
uv tool install ./<repo>/christory
```

Verify:

```sh
which christory   # -> ~/.local/bin/christory
christory          # launches the TUI
```

Reinstall after upstream updates:

```sh
uv tool install --reinstall git+https://github.com/<owner>/<repo>.git#subdirectory=christory
```

Uninstall:

```sh
uv tool uninstall christory
```

> Make sure `~/.local/bin` is on your `PATH`. `uv tool install` prints a hint if it isn't.

### Without uv

```sh
pipx install ./christory
```

…or with plain pip into a venv of your choice:

```sh
pip install ./christory
```

## Usage

Just run:

```sh
christory
```

Three filter inputs at the top narrow the result set independently:

- **search** — matches URL **and** title (case-insensitive `LIKE %term%`)
- **domain** — matches URL only
- **date** — accepts:
  - **prefix** — `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` (e.g. `2026-05`)
  - **range** — `YYYY-MM-DD..YYYY-MM-DD` (e.g. `2026-05-01..2026-05-15`)
  - **half-open** — `A..` (from A onwards) or `..B` (up to B)
  - Press `Enter` here to open a calendar picker.

### Keybindings

```
Filter  : /: focus search   tab: next field   ↓/esc: leave filter
          enter on date: calendar
          date syntax: YYYY[-MM[-DD]]  ·  A..B / A.. / ..B
Move    : j/↓: down   k/↑: up
          PgUp/Ctrl-U: prev page   PgDn/Ctrl-D: next page
          g: go to top   G: go to bottom
Row     : enter: open URL   i: info   c: copy URL   a: copy all
View    : s/S: sort col / dir   r: refresh   b: browser
          q or Ctrl-C: quit   esc: close modal
```

### Browser picker

Press `b` to open the browser picker. Inside:

- `↑/↓` `j/k` move cursor
- `c`/`b`/`h` jump-select Chrome / Brave / Helium
- `Enter` switch to highlighted browser (keeps active filters)
- `d` mark highlighted browser as the default for future launches
- `Esc` close

The default-browser preference is saved to `~/.config/christory/settings.json`.

### Calendar picker

When focused on the date filter, `Enter` opens a month calendar:

- `←/h` `→/l` — day -1 / +1
- `↑/k` `↓/j` — week -1 / +1
- `[` `]` — month -1 / +1
- `{` `}` — year -1 / +1
- `t` — jump to today
- `s` — set range **start** to highlighted day
- `e` — set range **end** to highlighted day
- `Enter` — pick highlighted date (single day), `Esc` — close

Setting both `s` and `e` writes an `A..B` range back to the date input
(picking a single `Enter` day collapses to a prefix filter).

## Configuration

Edit constants in the module shown:

| Constant               | Module      | Default                    | Purpose                                              |
| ---------------------- | ----------- | -------------------------- | ---------------------------------------------------- |
| `DEFAULT_HISTORY_PATH` | `db.py`     | macOS default profile path | Source SQLite DB                                     |
| `ROW_LIMIT`            | `db.py`     | `10_000`                   | Max rows returned by a single query                  |
| `SHOW_VISITS`          | `config.py` | `False`                    | Show the `Visits` count column                       |
| `VISITED_WIDTH`        | `config.py` | `16`                       | Width of the `Date` column                           |
| `VISITS_WIDTH`         | `config.py` | `7`                        | Width of the `Visits` column (when shown)            |
| `MIN_TEXT_WIDTH`       | `config.py` | `20`                       | Min width for `Title` / `URL` columns                |
| `MARQUEE_DELAY`        | `config.py` | `1.0`                      | Seconds before focused-row text starts scrolling     |
| `MARQUEE_INTERVAL`     | `config.py` | `0.25`                     | Seconds between marquee frames                       |
| `ACCENT`               | `theme.py`  | `"#fa841a"`                | Brand color (modal borders, cursor, header, keys)    |
| `KEY_HIGHLIGHT`        | `theme.py`  | `ACCENT`                   | Color used for key bindings in the footer            |

Modules live under `christory/` — e.g. `christory/config.py`.

After editing, reinstall: `uv tool install --reinstall .` (from the project dir).

## Development

```sh
git clone https://github.com/<owner>/<repo>.git
cd <repo>/christory
uv sync                  # creates .venv with textual + dev deps
uv run christory         # run from source
```

`uv sync` materializes a local `.venv/` so editors / language servers (basedpyright, Pyright, Pylance, Ruff) can resolve imports.

### Build a wheel / sdist

```sh
uv build
# -> dist/christory-0.1.0-py3-none-any.whl
# -> dist/christory-0.1.0.tar.gz
```

Test the built wheel in isolation:

```sh
uv tool install dist/christory-0.1.0-py3-none-any.whl
```

## How it works (brief)

1. On launch, the Chrome `History` SQLite DB is copied to `$TMPDIR/chrome_history_tui.db` (Chrome locks the live DB while running; the copy is read-only).
2. A single query fetches up to `ROW_LIMIT` rows — `text` and `domain` use `LIKE`, while the date input is parsed by `DateFilter` (`christory/date_filter.py`) into either a `LIKE` prefix or a `>=` / `<=` range clause.
3. Results render in a Textual `DataTable` with sortable columns (sort indicators `▼`/`▲` on the active column).
4. The focused row's overflowing title/URL scrolls (marquee) after `MARQUEE_DELAY` and pauses while a modal is open.
5. `Enter` on a row opens the URL via the OS default handler; `c`/`a` push URL or full row info to the clipboard (OSC52 first, `pbcopy` fallback).

## License

MIT
