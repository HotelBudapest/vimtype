"""Typing state and scoring, independent of terminal input and rendering."""

from dataclasses import dataclass, field
import random
from .pools import POOLS, load_pool


@dataclass
class Settings:
    mode: str = "time"
    duration: int = 30
    count: int = 25
    punctuation: bool = False
    numbers: bool = False
    theme: str = "serika"
    pool: str = "english"

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
            "pool": POOLS,
        }.items():
            value = data.get(key)
            if type(value) is type(choices[0]) and value in choices:
                setattr(settings, key, value)
        return settings


def generate_words(settings, rng=None):
    rng = rng or random.Random()
    words = []
    pool = load_pool(settings.pool)
    for _ in range(settings.count if settings.mode == "words" else 100):
        word = rng.choice(pool)
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
