# vimtype

A Vim-first terminal typing game inspired by [Monkeytype](https://github.com/monkeytypegame/monkeytype).
Navigate with motions, enter insert mode to type, and configure tests with `:` commands.
No mouse, arrow keys, runtime dependencies, network requests, or account required.

This is an independent implementation, not an official Monkeytype client or a fork.
No Monkeytype code, branding assets, or word lists are bundled. It does not sync
with Monkeytype accounts or claim full feature parity.

## Run

Requires Python 3.10+ with curses, on macOS or Linux (Windows users can use WSL).
Use a terminal at least 64 columns by 20 rows.

```sh
cd /Users/arianislam/Documents/Projects/type
python3 -m vimtype
```

Press `i` to start typing. The timer begins with your first character.

```sh
python3 -m vimtype --words 25
python3 -m vimtype --time 60 --punctuation --numbers
python3 -m vimtype --theme nord
```

Optional installation for a `vimtype` command:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/vimtype
```

Alternatively, install globally in an isolated environment with `pipx install .`.
From a clone elsewhere, change into that clone's directory before running these commands.

## Controls

| Context | Keys | Action |
| --- | --- | --- |
| Normal | `i`, Enter | Start a fresh test in insert mode |
| Normal | `s` / `H` / `?` | Settings / history / help |
| Menus | `j` / `k` | Move down / up |
| Settings | `h` / `l` | Cycle the selected value |
| Menus | `gg` / `G` | First / last row |
| Normal | `:` | Command line |
| Normal | `q` | Quit |
| Insert | All printable keys | Type literally, including Vim keys |
| Insert | Space | Submit current word |
| Insert | Backspace / Ctrl-w | Erase character / current word |
| Insert | Esc | Abort test and return to normal mode |
| Test or result | Tab | Start a fresh test |
| Any | Ctrl-c | Quit and restore terminal |

In normal mode, `Esc` returns to the test screen. In the command line, it cancels
the command. Help and history scroll with `j/k` and jump with `gg/G`.

Commands: `:time 15`, `:time 30`, `:time 60`, `:time 120`, `:words 10`,
`:words 25`, `:words 50`, `:words 100`, `:punctuation on|off`, `:numbers on|off`,
`:theme serika|nord|mono`, `:start`, `:restart`, `:settings`, `:history`, `:help`, `:q`.

## Behavior and scoring

- Timed tests run for 15, 30, 60, or 120 seconds; word tests have 10, 25, 50, or 100 words.
- Correct characters are bright, pending text is dim, errors are red and underlined,
  and the caret is highlighted. Text scrolls as you progress.
- Space accepts incorrect words. Backspace can return to a submitted word.
  A word test finishes when the last word is correct, or when you submit it with Space.
- WPM credits entirely correct submitted words (with spaces) and the current word
  only if it is a correct prefix. Divide credited characters by five and elapsed minutes.
- Raw WPM counts printable keystrokes, including mistakes and retyped characters.
  Accuracy is correct keystrokes divided by all printable keystrokes; corrections
  do not erase earlier mistakes. These are this app's scoring rules, not a promise
  of identical Monkeytype scoring.
- Esc aborts rather than pauses. Aborted tests are not saved. Resizing never pauses
  an active timer. Tab generates a fresh test.
- Settings changed in the UI and the latest 500 completed results are stored in
  `$XDG_DATA_HOME/vimtype`, or `~/.local/share/vimtype` by default. Use `--data-dir PATH`
  for an isolated session. CLI flags override saved defaults for the session;
  subsequent settings changes in the UI save the current configuration.
- Practice vocabulary is English ASCII. Quotes, custom languages, and account sync
  are not implemented. Pasting is not blocked, so results are for personal practice.

## Development

```sh
python3 -m unittest discover -s tests -v
```

Tests cover scoring, timing, correction, command handling, persistence, and an
actual terminal session using a pseudo-terminal. The app uses Python's standard
library only.
