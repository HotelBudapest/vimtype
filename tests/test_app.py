from dataclasses import asdict
import tempfile
import unittest
from unittest.mock import Mock, patch

from vimtype.app import App
from vimtype.core import Settings
from vimtype.storage import Storage


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = Storage(self.temp.name)
        with patch.object(App, "colors"), patch("curses.set_escdelay"):
            self.app = App(Mock(), Settings(), self.storage)

    def test_vim_settings_and_commands(self):
        app = self.app
        app.key("s", 0)
        with patch.object(App, "colors"):
            app.key("l", 0)
        self.assertEqual(app.settings.mode, "words")
        app.key("G", 0)
        self.assertEqual(app.selected, 5)
        app.key("g", 0)
        app.key("g", 0)
        self.assertEqual(app.selected, 0)
        app.key("j", 0)
        self.assertEqual(app.selected, 1)
        app.key("k", 0)
        self.assertEqual(app.selected, 0)
        for char in ":words 10\n":
            app.key(char, 0)
        self.assertEqual(app.settings.count, 10)
        self.assertEqual(self.storage.settings().count, 10)

    def test_vim_letters_type_literally_and_escape_aborts(self):
        app = self.app
        app.key("i", 0)
        for char in "hjkl:q":
            app.key(char, 1)
        self.assertEqual(app.test.current, "hjkl:q")
        self.assertTrue(app.running)
        self.assertIsNone(app.command)
        app.key("\x1b", 2)
        self.assertFalse(app.insert)
        self.assertEqual(self.storage.history(), [])
        app.key("i", 3)
        self.assertIsNone(app.test.started)
        self.assertEqual(app.test.current, "")

    def test_result_is_saved_and_tab_restarts(self):
        app = self.app
        app.execute("words 10")
        app.start()
        app.test.words = ["hi"]
        app.key("h", 0)
        app.key("i", 1)
        self.assertEqual(app.page, "result")
        self.assertEqual(len(self.storage.history()), 1)
        app.key("\t", 2)
        self.assertTrue(app.insert)
        self.assertIsNone(app.test.started)

    def test_invalid_command_does_not_change_settings(self):
        before = asdict(self.app.settings)
        self.app.execute("time 900")
        self.assertEqual(asdict(self.app.settings), before)
        self.assertIn("Unknown", self.app.message)

    def test_command_escape_and_backspace(self):
        for char in ":helx\x7fp\x1b":
            self.app.key(char, 0)
        self.assertIsNone(self.app.command)
        self.assertEqual(self.app.page, "test")

    def test_corrupt_history_and_settings_recover(self):
        self.storage.write("history.json", [None, {}, {"date": "bad"}])
        self.storage.write("settings.json", {"duration": "wrong"})
        self.assertEqual(self.storage.history(), [])
        self.assertEqual(self.storage.settings(), Settings())
        self.storage.write("history.json", "invalid structure")
        self.assertEqual(self.storage.history(), [])

    def test_render_all_pages_and_small_terminal(self):
        self.app.styles = [0] * 5
        with patch("curses.curs_set"):
            for size in [(24, 80), (20, 64), (10, 40)]:
                self.app.screen.getmaxyx.return_value = size
                for page in ("test", "settings", "help", "history"):
                    self.app.page = page
                    self.app.render(0)

    def test_history_retains_latest_500(self):
        row = dict(date="2026-09-08", mode="words", length=10, wpm=50, raw=55, accuracy=99)
        self.storage.write("history.json", [row] * 500)
        self.storage.save_result(dict(row, wpm=60))
        self.assertEqual(len(self.storage.history()), 500)
        self.assertEqual(self.storage.history()[-1]["wpm"], 60)
