"""Dependency-free line rasterization in Unicode Braille or plain ASCII."""

import math


def line_chart(values, width, height, braille=True):
    """Return (rows, point cells, lower bound, upper bound)."""
    if not values or width < 2 or height < 2:
        raise ValueError("A chart needs values and at least 2 x 2 cells")
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Scores must be finite and nonnegative")
    low, high = min(values), max(values)
    padding = max(5, (high - low) * 0.15)
    lower = max(0, math.floor((low - padding) / 5) * 5)
    upper = math.ceil((high + padding) / 5) * 5
    sx, sy = (2, 4) if braille else (1, 1)
    w, h = width * sx, height * sy
    points = [(round(i * (w - 1) / (len(values) - 1)) if len(values) > 1 else w - 1,
               round((upper - v) / (upper - lower) * (h - 1)))
              for i, v in enumerate(values)]
    pixels = set(points)
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(abs(x1 - x0), abs(y1 - y0))
        for step in range(1, steps):
            pixels.add((round(x0 + (x1 - x0) * step / steps),
                        round(y0 + (y1 - y0) * step / steps)))
    masks = [[0] * width for _ in range(height)]
    bits = ((1, 8), (2, 16), (4, 32), (64, 128))
    for x, y in pixels:
        masks[y // sy][x // sx] |= bits[y % 4][x % 2] if braille else 1
    rows = ["".join(chr(0x2800 + mask) if braille and mask else "*" if mask else " "
                    for mask in row) for row in masks]
    return rows, [(x // sx, y // sy) for x, y in points], lower, upper
