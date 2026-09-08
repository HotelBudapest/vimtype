# vimtype

A Vim-first terminal typing game inspired by [Monkeytype](https://github.com/monkeytypegame/monkeytype).
Navigate with motions, enter insert mode to type, and configure tests with `:` commands.
No mouse, arrow keys, runtime dependencies, network requests, or account required.

This is an independent implementation, not an official Monkeytype client or a fork.
Monkeytype's English word lists are bundled with attribution and their GPL license.
No Monkeytype application code or branding assets are bundled. It does not sync
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
python3 -m vimtype --pool english_5k --words 25
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
| Normal | `:q` then Enter | Quit |
| Insert | All printable keys | Type literally, including Vim keys |
| Insert | Space | Submit current word |
| Insert | Backspace / Ctrl-w | Erase character / current word |
| Insert | Esc | Abort test and return to normal mode |
| Test | Tab | Start a fresh test |
| Results | `j/k`, `gg/G` | Scroll previous scores |
| Results | `:start` / `:continue` / `:q` | Next test / setup / quit (Enter to execute) |
| Any | Ctrl-c | Quit and restore terminal |

In normal mode, `Esc` returns to the test screen. In the command line, it cancels
the command. Help and history scroll with `j/k` and jump with `gg/G`.

Commands: `:time 15`, `:time 30`, `:time 60`, `:time 120`, `:words 10`,
`:words 25`, `:words 50`, `:words 100`, `:punctuation on|off`, `:numbers on|off`,
`:theme serika|nord|mono`, `:start`, `:restart`, `:continue`, `:settings`, `:history`, `:help`, `:q`.

## Results screen

Completed tests open a persistent score screen with WPM, accuracy, raw speed,
elapsed time, and errors. Queued input is discarded at completion. Ordinary
typing, `i`, Tab, Enter, Esc, and bare `q` cannot dismiss the score screen.
Use `:start` to start another test, `:continue` to return to setup, or `:q` to
quit, followed by Enter. Ctrl-c remains an emergency exit from any screen.

Previous scores appear newest first below the latest result. Move the tinted
selection row with `j/k`, or jump with `gg/G`. The list scrolls when the selection
reaches the edge; the same selection works on the history screen.
The connected ASCII graph shows up to 40 recent WPM scores, oldest
to newest, for the same pool, mode, test length, punctuation, and numbers
settings as the latest result. Labeled horizontal grid lines show WPM on a scale
from zero to a rounded upper bound. The horizontal axis labels older and latest
test numbers; `o` marks previous results and the highlighted `*` is your latest.
Average, best, and change from the previous matching test summarize the displayed
scores. The graph grows taller with the terminal. The list includes all
previous settings, while legacy results without pool metadata are excluded
from the graph. History is limited to the latest 500 saved tests.

## Monkeytype word pools

Choose `english` (the default 200 words), `english_1k`, `english_5k`,
`english_10k`, `english_25k`, or `english_450k`. These are the exact upstream
JSON resources, bundled offline, with original spelling and capitalization.
Larger pools introduce a broader vocabulary. The names are Monkeytype's nominal
sizes; 10k currently contains 9,944 entries, 25k has 24,141, and 450k has 450,029.

Use `--pool english_10k` at launch, `:pool english_10k` inside the app, or
`s`, then `G` to select **word pool**, and `h/l` to change it. The selected pool
is saved with settings and new results. Older results are labeled `legacy`
because they used vimtype's original vocabulary.

Pool selection applies to both timed and word-count tests, including new words
generated during a timed test. Punctuation and numbers still work as modifiers.
Only the resources match Monkeytype; random selection and scoring remain vimtype's.
Monkeytype's separate normal/expert/master failure rules are not implemented.

Resource provenance, exact counts, and checksums are in
[NOTICE.md](vimtype/data/NOTICE.md). Original vimtype code is MIT licensed;
bundled Monkeytype resources retain [GPL-3.0](vimtype/data/LICENSE.monkeytype).

## Behavior and scoring

- Timed tests run for 15, 30, 60, or 120 seconds; word tests have 10, 25, 50, or 100 words.
- Correctly typed characters are greyed out, remaining text is bright, errors are red and underlined,
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
