"""Typing state and scoring, independent of terminal input and rendering."""

from dataclasses import dataclass, field
import random


# Original small practice vocabulary; no upstream code or word lists are bundled.
WORDS = """
the be to of and a in that have it for with on as you do at this but by
from they we say her she or an will my one all would there their what so
up out if about who get which go me when make can like time no just him
know take people into year your good some could them see other than then
now look only come its over think also back after use two how our work
first well way even new want because these give day most us is are was
been had were has did may more very much still long little own last
find here thing many world life hand part place case week company system
program question night point home water room mother area money story fact
month lot right study book eye job word business issue side kind head house
service friend power hour game line end member law car city community name
team minute idea kid body information nothing ago lead social understand
whether watch together follow around parent stop face anything create public
already speak others read level allow office spend door health person art
sure such change morning walk reason low win research girl early food before
moment air teacher force education foot boy age policy process music market
sense nation plan college interest course experience effect class control care
field development role effort rate heart light voice wife police mind price
report decision son view relationship town road arm difference value building
action model season society tax director position player record paper space
ground form event official matter center couple project activity court oil
picture situation cost industry figure street image phone data cover practice
piece land product doctor wall patient worker news test movie north love
support technology step baby computer type attention film tree source red
nearly organization choose cause hair century evidence window listen culture
chance brother energy period summer realize hundred available plant likely
opportunity term short letter condition choice single rule daughter south
husband floor campaign material population economy call medical hospital church
close thousand risk current fire future wrong involve anyone increase security
bank myself certainly west sport board seek subject officer private rest deal
fight throw top quickly past goal second bed order author fill focus drop
sound note fine near movement page enter return open write build learn calm
river ocean mountain forest cloud rain wind sky green blue bright quiet clear
small large simple fast slow warm cold code terminal normal motion cursor
""".split()


@dataclass
class Settings:
    mode: str = "time"
    duration: int = 30
    count: int = 25
    punctuation: bool = False
    numbers: bool = False
    theme: str = "serika"

    @classmethod
    def from_dict(cls, data):
        settings = cls()
        if not isinstance(data, dict):
            return settings
        for key, choices in {
            "mode": ("time", "words"),
            "duration": (15, 30, 60, 120),
            "count": (10, 25, 50, 100),
            "punctuation": (False, True),
            "numbers": (False, True),
            "theme": ("serika", "nord", "mono"),
        }.items():
            value = data.get(key)
            if type(value) is type(choices[0]) and value in choices:
                setattr(settings, key, value)
        return settings


def generate_words(settings, rng=None):
    rng = rng or random.Random()
    words = []
    for _ in range(settings.count if settings.mode == "words" else 100):
        word = rng.choice(WORDS)
        if settings.numbers and rng.random() < 0.15:
            word = str(rng.randint(0, 999))
        if settings.punctuation and rng.random() < 0.25:
            word = word.capitalize() + rng.choice([".", ",", "?", "!"])
        words.append(word)
    return words


@dataclass
class TypingTest:
    settings: Settings
    words: list[str]
    entries: list[str] = field(default_factory=lambda: [""])
    started: float | None = None
    finished: float | None = None
    keystrokes: int = 0
    correct_keystrokes: int = 0

    @property
    def index(self):
        return len(self.entries) - 1

    @property
    def current(self):
        return self.entries[-1]

    def elapsed(self, now):
        return 0.0 if self.started is None else max(0.0, (self.finished if self.finished is not None else now) - self.started)

    def tick(self, now):
        if self.started is not None and self.finished is None and self.settings.mode == "time":
            if now - self.started >= self.settings.duration:
                self.finished = self.started + self.settings.duration
        return self.finished is not None

    def feed(self, char, now):
        if self.tick(now):
            return
        if char == " " and not self.current:
            return
        if not (char.isascii() and char.isprintable()):
            return
        if self.started is None:
            self.started = now
        self.keystrokes += 1
        target = self.words[self.index]
        if char == " ":
            self.correct_keystrokes += self.current == target
            if self.settings.mode == "words" and self.index == len(self.words) - 1:
                self.finished = now
                return
            self.entries.append("")
            if self.index >= len(self.words) - 10 and self.settings.mode == "time":
                self.words.extend(generate_words(self.settings))
        else:
            pos = len(self.current)
            self.correct_keystrokes += pos < len(target) and char == target[pos]
            # Bound input length so an accidental key repeat cannot break layout.
            if len(self.current) < 40:
                self.entries[-1] += char
            if self.settings.mode == "words" and self.index == len(self.words) - 1 and self.current == target:
                self.finished = now

    def erase(self, whole_word=False):
        if self.finished is not None:
            return
        if not self.current and self.index:
            self.entries.pop()
        else:
            self.entries[-1] = "" if whole_word else self.current[:-1]

    def stats(self, now):
        seconds = self.elapsed(now)
        correct = 0
        # WPM credits correct submitted words and a correct current prefix.
        for index, entry in enumerate(self.entries):
            target = self.words[index]
            if index < self.index:
                if entry == target:
                    correct += len(target) + 1
            elif target.startswith(entry):
                correct += len(entry)
        minutes = seconds / 60
        return {
            "wpm": round(correct / 5 / minutes, 1) if minutes else 0.0,
            "raw": round(self.keystrokes / 5 / minutes, 1) if minutes else 0.0,
            "accuracy": round(100 * self.correct_keystrokes / self.keystrokes, 1) if self.keystrokes else 100.0,
            "seconds": round(seconds, 1),
            "keystrokes": self.keystrokes,
            "errors": self.keystrokes - self.correct_keystrokes,
        }
