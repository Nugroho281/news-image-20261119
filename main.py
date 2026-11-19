#!/usr/bin/env python3
"""Deliver the news-image-20261119 entry picture to the grader.

The whole entry is a single front-page image, entry.png, kept next to
this script: one page summing up the world news of Thursday
19 November 2026 in 44 stories — a hero report, six illustrated
panels, a numbers strip and 37 short wire briefs.

Running this program does three things, in order:

1. It inspects the picture against the competition's intake gate
   (a PNG or JPEG of at most 1 MiB whose sides are at most 1024 px)
   and refuses to continue when the picture does not fit.
2. It streams the picture into the output directory the grader
   provides ($MAKEFUN_OUTPUT_DIR, or /output when that variable is
   unset), under the name entry.png.
3. It fingerprints the delivered file with SHA-256 and compares the
   fingerprint with the source bytes, so a truncated or altered copy
   is reported instead of silently accepted.

Nothing here touches the network or the clock; the standard library
is all it needs, and repeated runs deliver identical bytes.
"""

import hashlib
import os
import shutil
import struct
import sys
from pathlib import Path

BYTE_LIMIT = 1 << 20  # 1 MiB intake cap
SIDE_LIMIT = 1024     # no side of the picture may exceed this
CHUNK = 64 * 1024     # streaming block size for copies and hashing

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
# Start-of-frame markers that carry the picture's dimensions.
JPEG_SOF = frozenset((0xC0, 0xC1, 0xC2))
# Markers with no length field and no payload (TEM, RST0-RST7, SOI, EOI).
JPEG_BARE = frozenset([0x01, 0xD8, 0xD9] + list(range(0xD0, 0xD8)))


class Reject(Exception):
    """The picture does not fit the intake gate."""


def png_dimensions(blob: bytes) -> tuple[int, int]:
    """Read width and height from the IHDR chunk of a PNG byte string."""
    if len(blob) < 8 + 8 + 13:
        raise Reject("PNG ends before its IHDR chunk is complete")
    chunk_len, chunk_type = struct.unpack(">I4s", blob[8:16])
    if chunk_type != b"IHDR" or chunk_len != 13:
        raise Reject("first PNG chunk is not a 13-byte IHDR")
    return struct.unpack(">II", blob[16:24])


def jpeg_dimensions(blob: bytes) -> tuple[int, int]:
    """Walk JPEG markers until a start-of-frame marker gives the size."""
    pos = 2  # the SOI marker itself was already matched by the caller
    while pos + 1 < len(blob):
        if blob[pos] != 0xFF:
            raise Reject(f"JPEG marker expected at offset {pos}")
        marker = blob[pos + 1]
        if marker in JPEG_BARE:
            pos += 2
            continue
        if pos + 4 > len(blob):
            raise Reject("JPEG segment header is cut short")
        seg_len = struct.unpack(">H", blob[pos + 2:pos + 4])[0]
        if marker in JPEG_SOF:
            if pos + 9 > len(blob):
                raise Reject("JPEG start-of-frame segment is cut short")
            height, width = struct.unpack(">HH", blob[pos + 5:pos + 9])
            return width, height
        if marker == 0xDA:
            raise Reject("JPEG scan data starts before any frame header")
        pos += 2 + seg_len
    raise Reject("no start-of-frame marker found in JPEG")


def measure(blob: bytes) -> tuple[int, int]:
    """Validate the raw picture against the gate; return (width, height)."""
    if len(blob) == 0:
        raise Reject("the picture file is empty")
    if len(blob) > BYTE_LIMIT:
        raise Reject(f"picture is {len(blob)} bytes; the cap is {BYTE_LIMIT}")
    if blob.startswith(PNG_SIGNATURE):
        width, height = png_dimensions(blob)
    elif blob.startswith(JPEG_SOI):
        width, height = jpeg_dimensions(blob)
    else:
        raise Reject("picture is neither PNG nor JPEG")
    if width == 0 or height == 0:
        raise Reject(f"picture declares a zero side ({width}x{height})")
    if width > SIDE_LIMIT or height > SIDE_LIMIT:
        raise Reject(f"picture is {width}x{height}; the cap is {SIDE_LIMIT} per side")
    return width, height


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def run() -> int:
    picture = Path(__file__).resolve().with_name("entry.png")
    if not picture.is_file():
        print(f"error: entry picture not found at {picture}", file=sys.stderr)
        return 2
    blob = picture.read_bytes()
    try:
        width, height = measure(blob)
    except Reject as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    delivered = out_dir / "entry.png"
    with picture.open("rb") as src, delivered.open("wb") as dst:
        shutil.copyfileobj(src, dst, CHUNK)

    if fingerprint_file(delivered) != fingerprint(blob):
        print("error: delivered file does not match the validated picture",
              file=sys.stderr)
        return 1
    print(f"delivered {delivered} ({len(blob)} bytes, {width}x{height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
