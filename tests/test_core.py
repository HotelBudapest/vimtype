import random
import unittest

from vimtype.core import Settings, TypingTest, generate_words


class TypingTests(unittest.TestCase):
    def test_clock_starts_on_first_printable_character(self):
        test = TypingTest(Settings(), ["hello"] * 100)
        test.feed("\n", 1)
        test.feed(" ", 2)
        self.assertIsNone(test.started)
        test.feed("h", 10)
        self.assertEqual(test.started, 10)
        self.assertEqual(test.elapsed(12), 2)

    def test_exact_score_and_final_word_completion(self):
        test = TypingTest(Settings(mode="words"), ["hello", "world"])
        for char in "hello ":
            test.feed(char, 0)
        for char in "world":
            test.feed(char, 12)
        self.assertEqual(test.finished, 12)
        self.assertEqual(test.stats(100), {
            "wpm": 11.0, "raw": 11.0, "accuracy": 100.0,
            "seconds": 12, "keystrokes": 11, "errors": 0,
        })

    def test_deadline_is_exact_and_late_input_ignored(self):
        test = TypingTest(Settings(duration=15), ["hello"] * 100)
        test.feed("h", 10)
        test.feed("e", 26)
        self.assertEqual(test.current, "h")
        self.assertEqual(test.finished, 25)
        self.assertEqual(test.elapsed(500), 15)
        test.erase()
        self.assertEqual(test.current, "h")

    def test_correction_keeps_error_in_accuracy(self):
        test = TypingTest(Settings(mode="words"), ["hi"])
        test.feed("x", 0)
        test.erase()
        test.feed("h", 1)
        test.feed("i", 2)
        self.assertEqual(test.stats(2)["accuracy"], 66.7)
        self.assertEqual(test.stats(2)["errors"], 1)

    def test_incorrect_words_are_not_credited(self):
        test = TypingTest(Settings(mode="words"), ["hi", "go"])
        for char in "hx ":
            test.feed(char, 0)
        test.feed("g", 60)
        self.assertEqual(test.stats(60)["wpm"], 0.2)

    def test_backspace_can_correct_previous_word(self):
        test = TypingTest(Settings(mode="words"), ["hello", "world"])
        for char in "hellx ":
            test.feed(char, 0)
        test.erase()
        test.erase()
        test.feed("o", 1)
        self.assertEqual(test.current, "hello")
        test.erase(whole_word=True)
        self.assertEqual(test.current, "")
        self.assertEqual(test.index, 0)

    def test_wrong_final_word_can_be_submitted(self):
        test = TypingTest(Settings(mode="words"), ["hi"])
        test.feed("x", 0)
        test.feed(" ", 1)
        self.assertEqual(test.finished, 1)
        self.assertEqual(test.stats(1)["wpm"], 0)

    def test_time_mode_generates_more_words(self):
        test = TypingTest(Settings(), ["a"] * 12)
        for char in "a a a a ":
            test.feed(char, 0)
        self.assertGreater(len(test.words), 12)

    def test_settings_reject_invalid_types_and_values(self):
        self.assertEqual(Settings.from_dict({"mode": "oops", "duration": True, "numbers": 1}), Settings())
        self.assertEqual(Settings.from_dict([]), Settings())

    def test_generator_is_reproducible_and_supports_modifiers(self):
        settings = Settings(mode="words", count=100, punctuation=True, numbers=True)
        words = generate_words(settings, random.Random(1))
        self.assertEqual(words, generate_words(settings, random.Random(1)))
        self.assertEqual(len(words), 100)
        self.assertTrue(any(any(c.isdigit() for c in word) for word in words))
        self.assertTrue(any(word.endswith((".", ",", "?", "!")) for word in words))

    def test_adjacent_words_differ_and_capitalization_is_opt_in(self):
        settings = Settings(mode="words", count=100)
        words = generate_words(settings, random.Random(8))
        self.assertTrue(all(word == word.lower() for word in words))
        self.assertTrue(all(left.lower() != right.lower() for left, right in zip(words, words[1:])))
        with_caps = generate_words(Settings(mode="words", count=100, capitalization=True, punctuation=True), random.Random(8))
        self.assertTrue(any(word[0].isupper() for word in with_caps if word[0].isalpha()))
        punctuated = generate_words(Settings(mode="words", count=100, punctuation=True), random.Random(8))
        self.assertTrue(all(left.rstrip(".,?!").lower() != right.rstrip(".,?!").lower()
                            for left, right in zip(punctuated, punctuated[1:])))
