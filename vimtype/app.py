"""Curses UI: explicit normal/insert modes and keyboard-only controls."""

import argparse
import curses
from dataclasses import replace
from datetime import datetime, timezone
import math
import sys
import time

from . import __version__
from .core import TypingTest, generate_words
from .storage import Storage
from .pools import POOLS


HELP = [
    "GETTING AROUND",
    "j / k       move down / up in settings and history",
    "h / l       change the selected setting",
    "gg / G      jump to the first / last row",
    "i / Enter   enter insert mode and start a fresh test",
    "s           open settings",
    "H           open local result history",
    "?           show this help",
    ":           open the command line",
    ":q + Enter  quit from normal mode",
    "",
    "WHILE TYPING (INSERT MODE)",
    "All printable keys type literally, including h j k l.",
    "The clock starts on the first character, not on i.",
    "Space       submit a word, including an incorrect word",
    "Backspace   erase; cross back into the previous word",
    "Ctrl-w      erase the current word",
    "Tab         restart with fresh words",
    "Esc         abort and return to normal mode",
    "Ctrl-c      quit from any screen",
    "",
    "COMMANDS",
    ":time 15|30|60|120      choose a timed test",
    ":words 10|25|50|100    choose a word-count test",
    ":punctuation on|off   toggle punctuation",
    ":numbers on|off       toggle numbers",
    ":theme serika|nord|mono",
    ":pool english|english_1k|english_5k|english_10k",
    "      english_25k|english_450k",
    ":start  :restart  :settings  :history  :help  :q",
    "",
    "RESULTS",
    "Results stay open until a command is entered.",
    "j/k and gg/G scroll previous scores.",
    ":start begins again; :continue returns to the test setup.",
    ":q quits. Bare keys, Enter, Tab and Esc cannot leave.",
    "WPM = correct submitted words + correct current prefix",
    "      (including credited spaces), / 5 / elapsed minutes.",
    "Raw = all printable keystrokes / 5 / elapsed minutes.",
    "Accuracy includes errors even after you correct them.",
    "Esc aborts a test; aborted tests are never recorded.",
    "Word tests finish on the final correct word, or Space",
    "to submit an incorrect final word. No pausing the timer.",
    "",
    "WORD POOLS / CREDITS",
    "English pools from Monkeytype contributors (GPL-3.0).",
    "Bundled unmodified; see data/NOTICE.md and",
    "data/LICENSE.monkeytype in the vimtype package.",
    "No warranty. Redistribution subject to the GPL license.",
    "Pools change vocabulary, not expert/master failure rules.",
]


class App:
    options = [
        ("mode", "test mode", ["time", "words"]),
        ("duration", "time / seconds", [15, 30, 60, 120]),
        ("count", "word count", [10, 25, 50, 100]),
        ("punctuation", "punctuation", [False, True]),
        ("numbers", "numbers", [False, True]),
        ("theme", "theme", ["serika", "nord", "mono"]),
        ("pool", "word pool", list(POOLS)),
    ]

    def __init__(self, screen, settings, storage):
        self.screen = screen
        self.settings = settings
        self.storage = storage
        self.page = "test"
        self.insert = False
        self.command = None
        self.selected = 0
        self.score_scroll = 0
        self.pending_g = False
        self.message = "Press i to begin.  ? for keys."
        self.running = True
        self.result = None
        self.history = storage.history()[::-1]
        self.fresh()
        screen.keypad(True)
        screen.timeout(50)
        curses.set_escdelay(25)
        self.colors()

    def colors(self):
        self.styles = [0, curses.A_DIM, curses.A_BOLD, curses.A_BOLD, curses.A_REVERSE, curses.A_REVERSE]
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                background = -1
            except curses.error:
                background = curses.COLOR_BLACK
            accent = curses.COLOR_CYAN if self.settings.theme == "nord" else curses.COLOR_YELLOW
            if self.settings.theme == "mono":
                accent = curses.COLOR_WHITE
            grey = 245 if curses.COLORS >= 256 else curses.COLOR_WHITE
            for pair, color in enumerate([curses.COLOR_WHITE, grey, accent, curses.COLOR_RED, accent], 1):
                curses.init_pair(pair, color, background)
            self.styles = [curses.color_pair(1), curses.color_pair(2) | (0 if curses.COLORS >= 256 else curses.A_DIM),
                           curses.color_pair(3) | curses.A_BOLD, curses.color_pair(4) | curses.A_UNDERLINE,
                           curses.color_pair(5) | curses.A_REVERSE]
            if curses.COLORS >= 256:
                curses.init_pair(6, curses.COLOR_WHITE, 238)
                self.styles.append(curses.color_pair(6))
            else:
                self.styles.append(curses.A_REVERSE)

    def fresh(self):
        self.test = TypingTest(replace(self.settings), generate_words(self.settings))
        self.result = None

    def start(self):
        self.fresh()
        self.page = "test"
        self.insert = True
        self.message = ""

    def save_settings(self):
        try:
            self.storage.save_settings(self.settings)
        except OSError as error:
            self.message = f"Settings could not be saved: {error.strerror}"

    def finish(self, now):
        self.insert = False
        self.page = "result"
        self.selected = 0
        self.pending_g = False
        self.command = None
        self.previous_results = self.storage.history()[::-1]
        self.result = self.test.stats(now)
        row = dict(self.result, date=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   mode=self.settings.mode,
                   length=self.settings.duration if self.settings.mode == "time" else self.settings.count,
                   punctuation=self.settings.punctuation, numbers=self.settings.numbers,
                   pool=self.test.settings.pool)
        self.result_record = row
        # Discard characters already queued when the timer or final word ended.
        try:
            curses.flushinp()
        except curses.error:
            pass
        try:
            self.storage.save_result(row)
            self.history = self.storage.history()[::-1]
            self.message = "Saved.  :start next test   :continue setup   :q quit"
        except OSError as error:
            self.message = f"Result not saved: {error.strerror}"

    def put(self, y, x, text, style=0):
        height, width = self.screen.getmaxyx()
        if 0 <= y < height and 0 <= x < width - 1:
            # Keep persisted text from introducing terminal controls.
            safe = "".join(c if c.isprintable() and c.isascii() else "?" for c in str(text))
            try:
                self.screen.addnstr(y, x, safe, width - x - 1, self.styles[style])
            except curses.error:
                pass

    def render(self, now):
        self.screen.erase()
        height, width = self.screen.getmaxyx()
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        if width < 64 or height < 20:
            self.put(0, 0, "vimtype needs a terminal at least 64 x 20.", 2)
            self.put(2, 0, "Resize to continue. Esc aborts; Ctrl-c quits.")
            self.put(4, 0, "An active test's timer continues while resized.", 1)
            self.screen.refresh()
            return
        left = max(3, (width - 90) // 2)
        self.put(1, left, "vimtype", 2)
        self.put(1, left + 10, "typing, at the speed of thought", 1)
        length = f"{self.settings.duration}s" if self.settings.mode == "time" else f"{self.settings.count} words"
        self.put(3, left, f"{self.settings.mode} / {length}   punctuation {'on' if self.settings.punctuation else 'off'}   numbers {'on' if self.settings.numbers else 'off'}", 1)
        self.put(4, left, f"pool / {self.settings.pool}", 1)
        if self.page == "test":
            self.render_test(now, left, width, height)
        elif self.page == "settings":
            self.put(5, left, "settings", 2)
            for index, (key, label, _) in enumerate(self.options):
                value = getattr(self.settings, key)
                value = ("on" if value else "off") if isinstance(value, bool) else str(value)
                self.put(7 + index, left, f"{'>' if index == self.selected else ' '} {label:20} {value:12}", 4 if index == self.selected else 0)
            self.put(14, left, "j/k select   h/l change   gg/G jump   i start", 1)
        elif self.page == "help":
            self.put(5, left, "keys & scoring   /   j k to scroll", 2)
            for offset, line in enumerate(HELP[self.selected:self.selected + height - 10]):
                self.put(7 + offset, left, line, 1 if not line or line[0].islower() else 0)
        elif self.page == "history":
            self.put(5, left, f"history / {len(self.history)} tests   j k to scroll", 2)
            self.render_scores(self.history, 7, left, width, height)
        elif self.page == "result":
            self.render_result(left, width, height)
        mode = "INSERT" if self.insert else "COMMAND" if self.command is not None else "RESULT" if self.page == "result" else "NORMAL"
        self.put(height - 3, left, f" {mode} ", 4)
        self.put(height - 3, left + 10, "Esc abort  Tab restart  Ctrl-w erase word" if self.insert else "j/k scroll   gg/G jump   : command to leave" if self.page == "result" else "i start   s settings   H history   ? help   :q quit", 1)
        if self.command is not None:
            visible = self.command[-(width - left - 3):]
            self.put(height - 2, left, ":" + visible)
            try:
                self.screen.move(height - 2, left + 1 + len(visible))
                curses.curs_set(1)
            except curses.error:
                pass
        else:
            self.put(height - 2, left, self.message, 1)
        self.screen.refresh()

    def render_result(self, left, width, height):
        stats = self.result
        self.put(5, left, f"TEST COMPLETE   {stats['wpm']:g} wpm   {stats['accuracy']:g}% accuracy", 2)
        self.put(6, left, f"raw {stats['raw']:g}   time {stats['seconds']:g}s   errors {stats['errors']}")
        # Compare like-for-like tests; history below still includes all settings.
        fields = ("mode", "length", "pool", "punctuation", "numbers")
        matching = [row for row in reversed(self.previous_results)
                    if all(row.get(key) == self.result_record.get(key) for key in fields)
                    and math.isfinite(row["wpm"]) and row["wpm"] >= 0]
        values = [row["wpm"] for row in matching] + [stats["wpm"]]
        total = len(values)
        values = values[-min(40, width - left - 12):]
        self.put(7, left, f"WPM trend / same settings / last {len(values)} tests", 2)
        change = f"{values[-1] - values[-2]:+.1f} vs prev" if len(values) > 1 else "first test"
        self.put(8, left, f"Avg {sum(values)/len(values):.1f}   Best {max(values):.1f}   {change}", 1)
        plot_height = max(2, min(8, height - 19))
        plot_width = min(78, width - left - 9)
        step = max(5, math.ceil(max(values) / (plot_height - 1) / 5) * 5)
        ceiling = step * (plot_height - 1)
        for level in range(plot_height):
            self.put(9 + level, left, f"{ceiling - level * step:5g} |" + "." * plot_width, 1)
        points = [(round(index * (plot_width - 1) / (len(values) - 1)) if len(values) > 1 else plot_width - 1,
                   (plot_height - 1) * (1 - value / ceiling)) for index, value in enumerate(values)]
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            for x in range(x0 + 1, x1):
                y = round(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
                self.put(9 + y, left + 7 + x, "-" if round(y0) == round(y1) else "/" if y1 < y0 else "\\", 0)
        for index, (x, y) in enumerate(points):
            self.put(9 + round(y), left + 7 + x, "*" if index == len(points) - 1 else "o", 2)
        axis_row = 9 + plot_height
        self.put(axis_row, left + 7, f"#{total - len(values) + 1} older", 1)
        latest = f"latest #{total} (*)"
        self.put(axis_row, left + 7 + plot_width - len(latest), latest, 2)
        count = len(self.previous_results)
        self.put(axis_row + 2, left, f"Previous scores / {count}   j/k select   gg/G jump", 2)
        if not count:
            self.put(axis_row + 4, left, "Your first result! Future scores will appear here.", 1)
            return
        self.render_scores(self.previous_results, axis_row + 3, left, width, height)

    def render_scores(self, rows, top, left, width, height):
        self.put(top, left, "  date (UTC)        pool           wpm   acc   mode", 1)
        if not rows:
            self.put(top + 2, left, "Complete a test to record your first result.", 1)
            return
        visible = max(1, height - top - 4)
        self.selected = min(self.selected, len(rows) - 1)
        self.score_scroll = min(self.score_scroll, self.selected)
        self.score_scroll = max(self.score_scroll, self.selected - visible + 1)
        self.score_scroll = min(self.score_scroll, max(0, len(rows) - visible))
        for index in range(self.score_scroll, min(len(rows), self.score_scroll + visible)):
            row = rows[index]
            pool = row.get("pool")
            pool = pool if isinstance(pool, str) and pool in POOLS else "legacy"
            selected = index == self.selected
            line = f"{'>' if selected else ' '} {row['date'][:16].replace('T', ' ')}  {pool:<12} {row['wpm']:5.1f} {row['accuracy']:5.1f}% {row['mode']} {row['length']}"
            span = min(90, width - left - 1)
            self.put(top + 1 + index - self.score_scroll, left, line[:span].ljust(span), 5 if selected else 0)

    def render_test(self, now, left, width, height):
        test = self.test
        stats = test.stats(now)
        remaining = f"{max(0, math.ceil(self.settings.duration - test.elapsed(now)))}s" if self.settings.mode == "time" else f"{min(test.index + 1, len(test.words))}/{len(test.words)}"
        self.put(6, left, f"{remaining}    {stats['wpm']:g} wpm    {stats['accuracy']:g}%", 2)
        available = min(90, width - left - 4)
        positions = []
        line, col = 0, 0
        for index, word in enumerate(test.words):
            entry = test.entries[index] if index < len(test.entries) else ""
            span = max(len(word), len(entry)) + 1
            if col and col + span > available:
                line, col = line + 1, 0
            positions.append((line, col))
            col += span
        current_line = positions[test.index][0]
        first_line = max(0, current_line - 1)
        visible_lines = min(5, height - 14)
        for index, word in enumerate(test.words):
            row, col = positions[index]
            if not first_line <= row < first_line + visible_lines:
                continue
            entry = test.entries[index] if index < len(test.entries) else ""
            for pos in range(max(len(word), len(entry))):
                target = word[pos] if pos < len(word) else ""
                typed = entry[pos] if pos < len(entry) else ""
                style = 0
                if typed:
                    style = 1 if typed == target else 3
                elif index < test.index:
                    style = 3
                if index == test.index and pos == len(entry):
                    style = 4
                self.put(9 + row - first_line, left + col + pos, typed or target, style)
            if index == test.index and len(entry) >= len(word):
                self.put(9 + row - first_line, left + col + len(entry), " ", 4)

    def navigate(self, key):
        limit = {"settings": len(self.options), "help": len(HELP), "history": len(self.history)}.get(self.page, 1)
        if key == "g":
            if self.pending_g:
                self.selected = 0
            self.pending_g = not self.pending_g
            return
        self.pending_g = False
        if key == "j":
            self.selected = min(max(0, limit - 1), self.selected + 1)
        elif key == "k":
            self.selected = max(0, self.selected - 1)
        elif key == "G":
            self.selected = max(0, limit - 1)
        elif key in ("h", "l") and self.page == "settings":
            name, _, values = self.options[self.selected]
            index = values.index(getattr(self.settings, name))
            setattr(self.settings, name, values[(index + (1 if key == "l" else -1)) % len(values)])
            self.colors()
            self.save_settings()
            self.fresh()

    def execute(self, command):
        parts = command.strip().split()
        if not parts:
            return
        name, *args = parts
        if name in ("q", "quit") and not args:
            self.running = False
        elif name in ("start", "restart") and not args:
            self.start()
        elif name == "continue" and not args:
            self.fresh()
            self.page, self.selected = "test", 0
            self.message = "Press i to begin.  ? for keys."
        elif name in ("settings", "history", "help") and not args:
            self.page, self.selected = name, 0
        elif name in ("time", "words") and len(args) == 1 and args[0].isdigit() and int(args[0]) in ([15, 30, 60, 120] if name == "time" else [10, 25, 50, 100]):
            self.settings.mode = name
            setattr(self.settings, "duration" if name == "time" else "count", int(args[0]))
            self.configured()
        elif name in ("punctuation", "numbers") and args in (["on"], ["off"]):
            setattr(self.settings, name, args[0] == "on")
            self.configured()
        elif name == "theme" and len(args) == 1 and args[0] in ("serika", "nord", "mono"):
            self.settings.theme = args[0]
            self.colors()
            self.configured()
        elif name == "pool" and len(args) == 1 and args[0] in POOLS:
            self.settings.pool = args[0]
            self.configured()
        else:
            self.message = f"Unknown command or value: {command}.  :help lists commands."

    def configured(self):
        self.message = "Settings updated.  i to begin."
        self.save_settings()
        self.fresh()
        self.page = "test"

    def key(self, key, now):
        if key == "\x03":
            self.running = False
            return
        if self.command is not None:
            if key == "\x1b":
                self.command = None
            elif key in ("\n", "\r", curses.KEY_ENTER):
                command, self.command = self.command, None
                self.execute(command)
            elif key in ("\x7f", "\b", curses.KEY_BACKSPACE):
                self.command = self.command[:-1]
            elif key == "\x17":
                self.command = self.command.rstrip().rsplit(" ", 1)[0] if " " in self.command.rstrip() else ""
            elif isinstance(key, str) and key.isascii() and key.isprintable() and len(self.command) < 160:
                self.command += key
            return
        if self.insert:
            if key == "\x1b":
                self.insert = False
                self.message = "Test aborted.  i starts a fresh test."
            elif key == "\t":
                self.start()
            elif key in ("\x7f", "\b", curses.KEY_BACKSPACE, "\x17"):
                self.test.erase(whole_word=key == "\x17")
            elif isinstance(key, str):
                self.test.feed(key, now)
            if self.test.finished is not None:
                self.finish(now)
            return
        if self.page == "result":
            if key == ":":
                self.command = ""
            elif key in ("j", "k", "g", "G"):
                if key == "j":
                    self.selected = min(max(0, len(self.previous_results) - 1), self.selected + 1)
                elif key == "k":
                    self.selected = max(0, self.selected - 1)
                elif key == "G":
                    self.selected = max(0, len(self.previous_results) - 1)
                elif self.pending_g:
                    self.selected = 0
                self.pending_g = key == "g" and not self.pending_g
            else:
                self.pending_g = False
            return
        if key in ("i", "\n", "\r", curses.KEY_ENTER, "\t"):
            self.start()
        elif key == ":":
            self.command = ""
        elif key in ("s", "H", "?"):
            self.page = {"s": "settings", "H": "history", "?": "help"}[key]
            self.selected = 0
        elif key == "\x1b":
            self.page, self.selected = "test", 0
            self.fresh()
        else:
            self.navigate(key)

    def run(self):
        while self.running:
            now = time.monotonic()
            if self.insert and self.test.tick(now):
                self.finish(now)
            self.render(now)
            try:
                key = self.screen.get_wch()
            except curses.error:
                continue
            now = time.monotonic()
            if self.insert and self.test.tick(now):
                self.finish(now)
                continue
            self.key(key, now)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Vim-first terminal typing practice. Run, then press i to type or ? for help.")
    parser.add_argument("--version", action="version", version=f"vimtype {__version__}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--time", type=int, choices=[15, 30, 60, 120], metavar="SECONDS")
    group.add_argument("--words", type=int, choices=[10, 25, 50, 100], metavar="COUNT")
    parser.add_argument("--punctuation", action="store_true", default=None)
    parser.add_argument("--numbers", action="store_true", default=None)
    parser.add_argument("--theme", choices=["serika", "nord", "mono"])
    parser.add_argument("--pool", choices=POOLS, help="Monkeytype English vocabulary pool (default: saved pool or english)")
    parser.add_argument("--data-dir", help="override the local settings/history directory")
    args = parser.parse_args(argv)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.exit(2, "vimtype needs an interactive terminal. Run python3 -m vimtype in your terminal.\n")
    storage = Storage(args.data_dir)
    settings = storage.settings()
    if args.time:
        settings.mode, settings.duration = "time", args.time
    if args.words:
        settings.mode, settings.count = "words", args.words
    for key in ("punctuation", "numbers", "theme", "pool"):
        if getattr(args, key) is not None:
            setattr(settings, key, getattr(args, key))
    try:
        curses.wrapper(lambda screen: App(screen, settings, storage).run())
    except KeyboardInterrupt:
        pass
    except curses.error as error:
        print(f"Could not initialize the terminal: {error}. Check TERM and use a supported terminal.", file=sys.stderr)
        return 1
    return 0
