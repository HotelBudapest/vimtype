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
        self.assertEqual(app.selected, len(app.options) - 1)
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

    def test_result_stays_open_until_explicit_command(self):
        app = self.app
        app.execute("words 10")
        app.start()
        app.test.words = ["hi"]
        app.key("h", 0)
        app.key("i", 1)
        self.assertEqual(app.page, "result")
        self.assertEqual(len(self.storage.history()), 1)
        result = app.result
        for char in "i\t\n\r\x1bqsH?leftover typing":
            app.key(char, 2)
            self.assertEqual(app.page, "result")
            self.assertFalse(app.insert)
            self.assertTrue(app.running)
            self.assertIs(app.result, result)
        for char in ":start\n":
            app.key(char, 3)
        self.assertTrue(app.insert)
        self.assertIsNone(app.test.started)

    def test_result_history_scroll_graph_and_continue(self):
        app = self.app
        row = dict(date="2026-09-08T12:00", mode="time", length=30,
                   pool="english", punctuation=False, numbers=False,
                   raw=50, accuracy=99)
        self.storage.write("history.json", [dict(row, wpm=n) for n in range(1, 13)])
        app.start()
        app.test.feed("a", 0)
        app.test.tick(30)
        app.finish(30)
        self.assertEqual(len(app.previous_results), 12)
        self.assertEqual(app.previous_results[0]["wpm"], 12)
        app.key("j", 31)
        self.assertEqual(app.selected, 1)
        app.key("G", 31)
        self.assertEqual(app.selected, 11)
        app.key("g", 31)
        app.key("g", 31)
        self.assertEqual(app.selected, 0)
        app.put = Mock()
        for height in (20, 24, 40):
            app.render_result(3, 64, height)
        text = " ".join(str(call.args[2]) for call in app.put.call_args_list)
        self.assertIn("last 13 tests", text)
        self.assertIn("Previous scores / 12", text)
        for char in ":continue\n":
            app.key(char, 32)
        self.assertEqual(app.page, "test")
        self.assertFalse(app.insert)

    def test_result_graph_filters_settings_and_handles_first_score(self):
        app = self.app
        app.start()
        app.test.feed("x", 0)
        app.test.tick(30)
        app.finish(30)
        app.put = Mock()
        app.render_result(3, 64, 20)
        text = " ".join(str(call.args[2]) for call in app.put.call_args_list)
        self.assertIn("last 1 tests", text)
        self.assertIn("Your first result", text)
        app.previous_results = [dict(app.result_record, pool="english_1k", wpm=100)]
        app.put.reset_mock()
        app.render_result(3, 64, 20)
        text = " ".join(str(call.args[2]) for call in app.put.call_args_list)
        self.assertIn("last 1 tests", text)
        for char in ":oops\n":
            app.key(char, 31)
        self.assertEqual(app.page, "result")
        for char in ":q\x1b":
            app.key(char, 31)
        self.assertEqual(app.page, "result")
        self.assertTrue(app.running)
        for char in ":q\n":
            app.key(char, 31)
        self.assertFalse(app.running)

    def test_score_selection_moves_before_scrolling_and_stays_visible(self):
        app = self.app
        app.page = "history"
        app.history = [dict(date=f"2026-09-{day:02d}T12:00", pool="english",
                            wpm=50, accuracy=99, mode="time", length=30)
                       for day in range(1, 21)]
        app.put = Mock()

        def selected_row():
            app.put.reset_mock()
            app.render_scores(app.history, 7, 3, 64, 24)
            highlighted = [call.args for call in app.put.call_args_list
                           if len(call.args) > 3 and call.args[3] == 5]
            self.assertEqual(len(highlighted), 1)
            self.assertTrue(highlighted[0][2].startswith("> "))
            self.assertLess(highlighted[0][0], 21)
            return highlighted[0]

        self.assertEqual(selected_row()[0], 8)
        app.key("j", 0)
        self.assertEqual(selected_row()[0], 9)
        self.assertEqual(app.score_scroll, 0)
        app.key("G", 0)
        self.assertIn("2026-09-20", selected_row()[2])
        self.assertGreater(app.score_scroll, 0)
        app.key("g", 0)
        app.key("g", 0)
        self.assertEqual(selected_row()[0], 8)
        self.assertEqual(app.score_scroll, 0)

    def test_expanded_graph_navigation_and_selection(self):
        app = self.app
        app.execute("graph")
        self.assertEqual(app.page, "test")
        row = dict(date="2026-09-08T12:00", mode="time", length=30,
                   pool="english", punctuation=False, numbers=False,
                   raw=60, accuracy=99, seconds=30, errors=1)
        self.storage.write("history.json", [dict(row, wpm=n) for n in (40, 50, 60)])
        app.execute("graph")
        self.assertEqual(app.page, "graph")
        app.put = Mock()
        app.render_result(3, 80, 24)
        self.assertTrue(any(len(call.args) > 3 and call.args[3] == 4 for call in app.put.call_args_list))
        app.key("j", 0)
        self.assertEqual(app.selected, 1)
        app.put.reset_mock()
        app.render_result(3, 80, 24)
        self.assertTrue(any("Selected #1: 40 WPM" in str(call.args[2]) for call in app.put.call_args_list))
        app.execute("graph ascii")
        self.assertFalse(app.graph_braille)
        app.execute("results")
        self.assertEqual(app.page, "result")
        app.execute("graph braille")
        self.assertTrue(app.graph_braille)
        for key in "i\tq\n\x1b":
            app.key(key, 0)
        self.assertEqual(app.page, "graph")
        self.assertTrue(app.running)

    def test_invalid_command_does_not_change_settings(self):
        before = asdict(self.app.settings)
        self.app.execute("time 900")
        self.assertEqual(asdict(self.app.settings), before)
        self.assertIn("Unknown", self.app.message)

    def test_pool_command_persists_and_records_selection(self):
        app = self.app
        app.execute("pool english_10k")
        self.assertEqual(self.storage.settings().pool, "english_10k")
        app.execute("pool invalid")
        self.assertEqual(app.settings.pool, "english_10k")
        app.execute("words 10")
        app.start()
        for word in list(app.test.words):
            for char in word + " ":
                app.key(char, 1)
        self.assertEqual(self.storage.history()[0]["pool"], "english_10k")

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
        self.app.styles = [0] * 6
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
