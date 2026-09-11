from importlib.resources import files
import hashlib
import random
import unittest

from vimtype.core import Settings, TypingTest, generate_words
from vimtype.pools import POOLS, load_pool


class PoolTests(unittest.TestCase):
    def test_bundles_match_pinned_upstream(self):
        expected = {
            "english": (200, "9eff3c4563d4409f4c18d6bd35963654570c72d688b4e01453eac916d614be1e"),
            "english_1k": (1000, "43508d6d63920e87d97762ef775b7419e36f7f3496351be3ea76f8421e52757d"),
            "english_5k": (5000, "d71fd5e0559e565337630a8f46a47db85d0fcae790ed6d2a878dcac137025ae3"),
            "english_10k": (9944, "525c06bb0a8d2d9158229f1a6371d2f8ac7eb005575594be42498e76f12ca7e3"),
            "english_25k": (24141, "599b288a3458f704f7109dfde96c9b82198e157dcd49b4e774af9320d1d7b575"),
            "english_450k": (450029, "0328b0f4a3979012d35f7388f6a6cf172e0867f7e59905a673ee7b7b9f3e98f9"),
        }
        for name, (count, digest) in expected.items():
            with self.subTest(pool=name):
                raw = files("vimtype").joinpath("data", name + ".json").read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                self.assertEqual(len(load_pool(name)), count)
                self.assertTrue(all(w and w.isascii() and not any(c.isspace() for c in w) and len(w) < 40 for w in load_pool(name)))

    def test_selection_and_timed_extension_use_selected_pool(self):
        for name in POOLS:
            with self.subTest(pool=name):
                pool = set(load_pool(name))
                settings = Settings(pool=name)
                words = generate_words(settings, random.Random(4))
                self.assertTrue(set(words) <= pool | {word.lower() for word in pool})
                test = TypingTest(settings, words[:12])
                for _ in range(4):
                    for char in test.words[test.index] + " ":
                        test.feed(char, 0)
                self.assertGreater(len(test.words), 12)
                self.assertTrue(set(test.words) <= pool | {word.lower() for word in pool})

    def test_settings_upgrade_and_invalid_pool(self):
        self.assertEqual(Settings.from_dict({"mode": "words"}).pool, "english")
        self.assertEqual(Settings.from_dict({"pool": "missing"}).pool, "english")
        self.assertEqual(Settings.from_dict({"pool": "english_25k"}).pool, "english_25k")
        with self.assertRaises(ValueError):
            load_pool("../LICENSE")
