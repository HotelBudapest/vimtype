# vimtype

A Vim-first terminal typing game inspired by [Monkeytype](https://github.com/monkeytypegame/monkeytype).
Navigate with motions, enter insert mode to type, and configure tests with `:` commands.
No mouse, arrow keys, runtime dependencies, network requests, or account required.

This is an independent implementation, not an official Monkeytype client or a fork.
Monkeytype's English word lists are bundled with attribution and their GPL license.
No Monkeytype application code or branding assets are bundled. It does not sync
with Monkeytype accounts or claim full feature parity.

## Install and run

vimtype requires Python 3.10 or newer and an interactive terminal with curses.
It runs on macOS and Linux. Windows users should use WSL2 with an Ubuntu (or
similar Linux) distribution; native Windows consoles do not provide the curses
module used by this app. Use a terminal at least 64 columns by 20 rows.

### macOS or Linux: run directly from a clone

Install Git and Python first if they are not already available. Verify both
commands before cloning:

```sh
git --version
python3 --version
```

Python must print `3.10` or a newer version. Then clone this repository, enter
the clone, and start vimtype:

```sh
git clone https://github.com/HotelBudapest/vimtype.git
cd vimtype
python3 -m vimtype
```

The command must be run from the clone when using this direct method. Press `i`
to start typing; the timer begins with your first character. Try launch options:

```sh
python3 -m vimtype --words 25
python3 -m vimtype --time 60 --punctuation --numbers
python3 -m vimtype --theme nord --pool english_5k
```

### macOS or Linux: install a `vimtype` command

This creates a project-local virtual environment, installs the package in
editable mode, and makes the `vimtype` command available whenever that
environment is activated. Run these commands from the cloned `vimtype` directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --editable .
source .venv/bin/activate
vimtype
```

After closing the terminal, activate it again from any directory with the
absolute path to the clone:

```sh
source /absolute/path/to/vimtype/.venv/bin/activate
vimtype --pool english_10k
```

Replace `/absolute/path/to/vimtype` with the directory created by `git clone`.
To leave the environment, run `deactivate`. To remove it later, change into
the clone and run `rm -rf .venv`; this only removes the virtual environment,
not your source or saved results. The editable install means source changes in
the clone are used immediately.

If you use pipx, the equivalent isolated install from the clone is:

```sh
pipx install .
vimtype
```

### Windows with WSL2

Open PowerShell as Administrator once and install WSL2 with Ubuntu:

```powershell
wsl --install -d Ubuntu
```

Restart if Windows asks you to, open **Ubuntu** from the Start menu, and run
the following inside the Linux shell (not PowerShell):

```sh
sudo apt update
sudo apt install --yes git python3 python3-venv python3-pip
git clone https://github.com/HotelBudapest/vimtype.git
cd vimtype
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --editable .
source .venv/bin/activate
vimtype
```

Use Windows Terminal to run the Ubuntu profile for the best interactive
experience. If `wsl --install` is unavailable, enable WSL2 through Microsoft’s
current Windows instructions, install an Ubuntu distribution, and then use the
Linux commands above.

### Data and terminal troubleshooting

Settings and the latest 500 completed tests are saved locally in
`$XDG_DATA_HOME/vimtype`, or `~/.local/share/vimtype` when that variable is
unset. Use `--data-dir /path/to/test-data` for a separate history. No account,
network connection, or runtime package is needed after installation.

If vimtype says it needs an interactive terminal, run it directly in a terminal
window rather than piping or redirecting its input. If it reports that the
terminal is too small, resize to at least 64 columns by 20 rows. If colors or
Braille graph cells look wrong, use `:graph ascii`; the app also falls back to
ASCII when the locale cannot encode Unicode.

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
| Other screens | Tab | Return to the test screen (normal mode) |
| Results | `j/k`, `gg/G` | Scroll previous scores |
| Results | `:start` / `:continue` / `:q` | Next test / setup / quit (Enter to execute) |
| Any | Ctrl-c | Quit and restore terminal |

In normal mode, `Esc` returns to the test screen. In the command line, it cancels
the command. Help and history scroll with `j/k` and jump with `gg/G`.

Commands: `:time 15`, `:time 30`, `:time 60`, `:time 120`, `:words 10`,
`:words 25`, `:words 50`, `:words 100`, `:punctuation on|off`, `:numbers on|off`,
`:capitalization on|off`,
`:theme serika|nord|mono`, `:start`, `:restart`, `:continue`, `:settings`, `:history`, `:help`, `:q`.

## Results screen

Completed tests open a persistent score screen with WPM, accuracy, raw speed,
elapsed time, and errors. Queued input is discarded at completion. Ordinary
typing, `i`, Enter, Esc, and bare `q` cannot dismiss the score screen. Tab
returns to the test screen in normal mode and prepares a fresh test.
Use `:start` to start another test, `:continue` to return to setup, or `:q` to
quit, followed by Enter. Ctrl-c remains an emergency exit from any screen.

Previous scores appear newest first below the latest result. Move the tinted
selection row with `j/k`, or jump with `gg/G`. The list scrolls when the selection
reaches the edge; the same selection works on the history screen.
The `H` history screen shows this list beside an all-tests WPM trend chart; its
selected row highlights the corresponding chart point when that score is visible.
The Braille line graph shows available matching WPM scores, oldest to newest,
for the same pool, mode, length, punctuation, and numbers settings as the result.
Its labeled WPM scale fits the scores with padding (it need not start at zero).
Sparse grid marks, average/best/change summaries, and a labeled latest score
help make the trend readable. Selecting a previous score highlights its graph
cell and displays its exact WPM; a note explains when its settings do not match.
Dense histories can place multiple scores in the same terminal cell.

Use `:graph` for an expanded chart and `:results` to return to the score list.
The expanded chart keeps `j/k` and `gg/G` selection and requires a command to
leave. You can also open `:graph` after launching the app to inspect the latest
saved result. Use `:graph ascii` if your font cannot display Braille, and
`:graph braille` to switch back. This choice lasts for the session. Non-Unicode
output defaults to ASCII. Graph rendering adds no runtime dependencies.

The list includes all previous settings, while unmatched legacy results are
excluded from the graph. History is limited to the latest 500 saved tests.

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
Adjacent words are always different (case-insensitive), so a pool cannot produce
the same word twice in a row. Capital letters are disabled by default: upstream's
`I` becomes `i`, and punctuation does not capitalize words unless capitalization
is enabled with `--capitalization`, `:capitalization on`, or the settings row.
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
  an active timer. Tab generates a fresh test from the test screen and returns to
  the test screen from every other screen.
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
