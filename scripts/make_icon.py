"""Generate the Xtobe app icon (pure stdlib PNG writer, no Pillow needed).
Dark void background + neon cyan X mark. Output: icon.png (256x256 RGB)."""
import struct
import zlib

W = H = 256
BG = (5, 7, 13)        # #05070d
NEON = (34, 211, 238)  # #22d3ee
GLOW = (12, 74, 110)

def pixel(x, y):
    d1 = abs(x - y)            # main diagonal
    d2 = abs(x + y - (W - 1))  # anti diagonal
    m = min(d1, d2)
    if m < 12:
        return NEON
    if m < 22:
        return GLOW
    # subtle inner frame
    if x in (10, W - 11) and 10 <= y < H - 10 or y in (10, H - 11) and 10 <= x < W - 10:
        return (27, 39, 64)
    return BG

def chunk(tag, payload):
    c = struct.pack(">I", len(payload)) + tag + payload
    return c + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

raw = b"".join(
    b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(W))
    for y in range(H)
)
png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    + chunk(b"IDAT", zlib.compress(raw, 9))
    + chunk(b"IEND", b"")
)
open("icon.png", "wb").write(png)
print("icon.png written:", len(png), "bytes")
