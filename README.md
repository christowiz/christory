# christory

A terminal UI for searching local Chrome history by text, domain, and date.

Reads `~/Library/Application Support/Google/Chrome/Default/History` (read-only, via a temp snapshot) and renders results in a sortable table with marquee-scrolling rows, a calendar date picker, and OSC52 clipboard support.

## Requirements

- macOS (Chrome history path is macOS-specific; trivial to port)
- Google Chrome installed, with at least one visit recorded for the `Default` profile
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (recommended) for install / dev workflows

## Install

Install as an isolated tool — places a real `christory` executable on your `PATH`:

```sh
uv tool install git+https://github.com/<owner>/<repo>.git#subdirectory=chrome-search-history-textual
```

Or from a local clone:

```sh
git clone https://github.com/<owner>/<repo>.git
uv tool install ./<repo>/chrome-search-history-textual
```

Verify:

```sh
which christory   # -> ~/.local/bin/christory
christory          # launches the TUI
```

Reinstall after upstream updates:

```sh
uv tool install --reinstall git+https://github.com/<owner>/<repo>.git#subdirectory=chrome-search-history-textual
```

Uninstall:

```sh
uv tool uninstall christory
```

> Make sure `~/.local/bin` is on your `PATH`. `uv tool install` prints a hint if it isn't.

### Without uv

```sh
pipx install ./chrome-search-history-textual
```

…or with plain pip into a venv of your choice:

```sh
pip install ./chrome-search-history-textual
```

## Usage

Just run:

```sh
christory
```

Three filter inputs at the top narrow the result set independently:

- **search** — matches URL **and** title (case-insensitive `LIKE %term%`)
- **domain** — matches URL only
- **date** — date prefix; accepts `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`. Press `Enter` here to open a calendar picker.

### Keybindings

```
General    : q / ctrl-c: quit  r: refresh  tab: switch focus
             /: focus search  enter: focus table / open url
             ↓ / esc: from filter → table  s/S: sort col / dir
Filter     : search: URL + title  domain: URL only
             date: prefix e.g. 2026-05-20 — or enter for calendar
Navigation : j/↓: down  k/↑: up
             PageUp / Ctrl-U: page up  PageDown / Ctrl-D: page down
             g: top  G: bottom
Commands   : i: info  c: copy URL  a: copy all
             enter: open URL  esc: dismiss modal
```

### Calendar picker

When focused on the date filter, `Enter` opens a month calendar:

- `←/h` `→/l` — day -1 / +1
- `↑/k` `↓/j` — week -1 / +1
- `[` `]` — month -1 / +1
- `{` `}` — year -1 / +1
- `t` — jump to today
- `Enter` — pick highlighted date, `Esc` — cancel

## Configuration

Edit constants near the top of `christory.py`:

| Constant            | Default | Purpose                                              |
| ------------------- | ------- | ---------------------------------------------------- |
| `CHROME_HISTORY`    | macOS default profile path | Source SQLite DB |
| `SHOW_VISITS`       | `False` | Show the `Visits` count column                       |
| `VISITED_WIDTH`     | `16`    | Width of the `Date` column                           |
| `VISITS_WIDTH`      | `7`     | Width of the `Visits` column (when shown)            |
| `MIN_TEXT_WIDTH`    | `20`    | Min width for `Title` / `URL` columns                |
| `MARQUEE_DELAY`     | `1.0`   | Seconds before focused-row text starts scrolling     |
| `MARQUEE_INTERVAL`  | `0.25`  | Seconds between marquee frames                      |
| `ROW_LIMIT`         | `10_000`| Max rows returned by a single query                  |

After editing, reinstall: `uv tool install --reinstall .` (from the project dir).

## Development

```sh
git clone https://github.com/<owner>/<repo>.git
cd <repo>/chrome-search-history-textual
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
2. A single query with three `LIKE` filters fetches up to `ROW_LIMIT` rows.
3. Results render in a Textual `DataTable` with sortable columns (sort indicators `▼`/`▲` on the active column).
4. The focused row's overflowing title/URL scrolls (marquee) after `MARQUEE_DELAY` and pauses while a modal is open.
5. `Enter` on a row opens the URL via the OS default handler; `c`/`a` push URL or full row info to the clipboard (OSC52 first, `pbcopy` fallback).

## License

MIT (or whichever you choose — add a `LICENSE` file).
