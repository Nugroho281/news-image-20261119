#!/usr/bin/env python3
"""news-image-20261119 entry program (Python 3, standard library only).

The entry is the front-page image beside this file, entry.png: one page
that sums up the world news of Thursday 19 November 2026 — 44 stories:
a hero report on the first Trump-Xi-Putin face-to-face meeting, six
illustrated panels, a by-the-numbers strip and 37 wire briefs. This
program copies that image, byte for byte, to the output path the grader
names: $MAKEFUN_OUTPUT_DIR/entry.png locally, /output/entry.png in the
grader's container. It reads nothing else and needs no network, so two
runs always produce identical bytes.
"""

import os
import shutil
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "entry.png"

# The competition's image gate: a whole PNG or JPEG, at most 1 MiB and
# 1024 x 1024 pixels. The program checks its own image against that gate
# before copying, so a bad asset fails loudly here instead of at intake.
MAX_BYTES = 1024 * 1024
MAX_SIDE = 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def check_image(data: bytes) -> None:
    if not data:
        raise ValueError("entry.png is empty")
    if len(data) > MAX_BYTES:
        raise ValueError(f"entry.png is {len(data)} bytes, over the 1 MiB cap")
    if data.startswith(PNG_MAGIC):
        # IHDR is the first chunk: width and height are big-endian uint32
        # at bytes 16..24 of the file.
        width, height = struct.unpack(">II", data[16:24])
    elif data.startswith(JPEG_MAGIC):
        width = height = 0  # dimensions not parsed for JPEG; magic is enough
    else:
        raise ValueError("entry.png is neither PNG nor JPEG")
    if width > MAX_SIDE or height > MAX_SIDE:
        raise ValueError(f"entry.png is {width}x{height}, over the 1024px cap")


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"missing entry image: {SOURCE}")
    data = SOURCE.read_bytes()
    check_image(data)
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    shutil.copyfile(SOURCE, target)
    # Post-copy guard: the grader must receive exactly the validated bytes.
    if target.read_bytes() != data:
        raise IOError("copied entry.png differs from the validated source")


if __name__ == "__main__":
    main()
