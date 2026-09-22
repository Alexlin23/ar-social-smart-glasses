"""Pixel layout: keep panels inside a safe area and away from all faces."""
from __future__ import annotations

# Rectangles use x, y, width, height throughout (same as the original pipeline).
def intersects(a, b):
    return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
            and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])


def safe_area(width, height, margin, top=44, bottom=50):
    pad = max(0, min(margin, width // 8, height // 8))
    return (pad, min(height, pad + top), max(0, width - 2 * pad),
            max(0, height - 2 * pad - top - bottom))


def place_panel(size, anchor, safe, obstacles):
    """Return a free rectangle or None. Omit content rather than cover a face."""
    width, height = size
    sx, sy, sw, sh = safe
    if width > sw or height > sh or min(width, height) <= 0:
        return None
    ax, ay, aw, ah = anchor
    candidates = [(ax + aw + 16, ay), (ax - width - 16, ay),
                  (ax, ay + ah + 16), (ax, ay - height - 16)]
    # Deterministic fallback grid for dense multi-person scenes.
    candidates += [(x, y) for y in range(sy, sy + sh - height + 1, 24)
                   for x in range(sx, sx + sw - width + 1, 24)]
    candidates += [(sx + sw - width, sy + sh - height)]
    for x, y in candidates:
        x = max(sx, min(int(x), sx + sw - width))
        y = max(sy, min(int(y), sy + sh - height))
        rect = (x, y, width, height)
        if not any(intersects(rect, obstacle) for obstacle in obstacles):
            return rect
    return None
