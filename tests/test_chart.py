import unittest

from vimtype.chart import line_chart


class ChartTests(unittest.TestCase):
    def test_bounds_and_endpoints_including_dense_series(self):
        for values in ([0], [50, 50], [30, 80, 20, 70], list(range(501))):
            for braille in (True, False):
                rows, points, lower, upper = line_chart(values, 40, 8, braille)
                self.assertEqual(len(rows), 8)
                self.assertTrue(all(len(row) == 40 for row in rows))
                self.assertLessEqual(lower, min(values))
                self.assertGreater(upper, max(values))
                self.assertEqual(points[-1][0], 39)
                for x, y in points:
                    self.assertTrue(0 <= x < 40 and 0 <= y < 8)
                    self.assertNotEqual(rows[y][x], " ")
                if not braille:
                    self.assertTrue(all(row.isascii() for row in rows))

    def test_braille_has_subcell_detail(self):
        rows, _, _, _ = line_chart([40, 60, 45, 70], 40, 5)
        symbols = set("".join(rows)) - {" "}
        self.assertGreater(len(symbols), 3)
        self.assertTrue(all(0x2801 <= ord(c) <= 0x28ff for c in symbols))

    def test_invalid_scores(self):
        for values in ([], [-1], [float("nan")], [float("inf")]):
            with self.assertRaises(ValueError):
                line_chart(values, 40, 5)
