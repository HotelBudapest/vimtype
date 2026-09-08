"""Local settings and history; atomic writes and tolerant reads."""

from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile

from .core import Settings


class Storage:
    def __init__(self, root=None):
        self.root = Path(root) if root else Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "vimtype"

    def read(self, name, fallback):
        try:
            return json.loads((self.root / name).read_text())
        except (OSError, ValueError):
            return fallback

    def write(self, name, value):
        self.root.mkdir(parents=True, exist_ok=True)
        filename = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.root, delete=False) as stream:
                filename = stream.name
                json.dump(value, stream, indent=2)
                stream.write("\n")
            os.replace(filename, self.root / name)
        finally:
            if filename and os.path.exists(filename):
                os.unlink(filename)

    def settings(self):
        return Settings.from_dict(self.read("settings.json", {}))

    def save_settings(self, settings):
        self.write("settings.json", asdict(settings))

    def history(self):
        data = self.read("history.json", [])
        if not isinstance(data, list):
            return []
        return [row for row in data if isinstance(row, dict)
                and isinstance(row.get("date"), str)
                and row.get("mode") in ("time", "words")
                and all(type(row.get(key)) in (int, float) for key in ("wpm", "raw", "accuracy", "length"))][-500:]

    def save_result(self, result):
        self.write("history.json", (self.history() + [result])[-500:])
