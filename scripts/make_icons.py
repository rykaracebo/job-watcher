"""Draw the app icons (three rising bars on navy) as PNG files, no image library needed.

    python scripts/make_icons.py
"""
import struct
import zlib
from pathlib import Path

NAVY, GOLD = (20, 40, 75), (184, 134, 11)


def png(size, bars):
    """bars: (x0, y0, x1, y1) rectangles as fractions of the icon, drawn in gold."""
    rects = [(round(a * size), round(b * size), round(c * size), round(d * size))
             for a, b, c, d in bars]
    raw = bytearray()
    for y in range(size):
        raw.append(0)                                   # PNG filter type: none
        for x in range(size):
            hit = any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in rects)
            raw.extend((*(GOLD if hit else NAVY), 255))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


# Full-size mark, and a smaller one that stays inside the 80% "safe zone" that
# Android crops to when it masks the icon into a circle or squircle.
FULL = [(0.20, 0.55, 0.38, 0.80), (0.41, 0.38, 0.59, 0.80), (0.62, 0.20, 0.80, 0.80)]
SAFE = [(0.30, 0.56, 0.42, 0.72), (0.44, 0.44, 0.56, 0.72), (0.58, 0.32, 0.70, 0.72)]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "icons"
    out.mkdir(exist_ok=True)
    for name, size, bars in [("icon-192.png", 192, FULL), ("icon-512.png", 512, FULL),
                             ("icon-maskable-512.png", 512, SAFE),
                             ("apple-touch-icon.png", 180, FULL)]:
        (out / name).write_bytes(png(size, bars))
        print("wrote", out / name)
