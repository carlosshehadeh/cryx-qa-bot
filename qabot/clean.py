"""Clean WAV copies: rewrite a WAV with only its `fmt ` and `data` chunks.

The audio bytes are copied unchanged, so the samples are bit-identical, and
no LIST/INFO, bext, iXML, id3 or content-credential (C2PA/JUMBF) chunk
survives. The original file is only ever read.
"""

import shutil
import struct
from pathlib import Path

from qabot.audio import read_chunks

KEEP = ("fmt ", "data")


def clean_copy(src, dst):
    src, dst = Path(src), Path(dst)
    if src.resolve() == dst.resolve():
        raise ValueError("refusing to overwrite the original file")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, "rb") as f:
        chunks = {c.id: c for c in reversed(read_chunks(f))}   # first of each id wins
        missing = [k for k in KEEP if k not in chunks]
        if missing:
            raise ValueError(f"{src.name}: no {' / '.join(missing)} chunk")
        f.seek(chunks["fmt "].offset)
        fmt = f.read(chunks["fmt "].size)
        data = chunks["data"]
        size = min(data.size, src.stat().st_size - data.offset)
        body = 4 + 8 + len(fmt) + (len(fmt) & 1) + 8 + size + (size & 1)
        tmp = dst.with_name(dst.name + ".part")
        with open(tmp, "wb") as out:
            out.write(b"RIFF" + struct.pack("<I", body) + b"WAVE")
            out.write(b"fmt " + struct.pack("<I", len(fmt)) + fmt + (b"\0" if len(fmt) & 1 else b""))
            out.write(b"data" + struct.pack("<I", size))
            f.seek(data.offset)
            left = size
            while left:
                block = f.read(min(left, 1 << 20))
                if not block:
                    raise ValueError(f"{src.name}: audio data is cut off")
                out.write(block)
                left -= len(block)
            if size & 1:
                out.write(b"\0")
    shutil.move(tmp, dst)
    return dst


def chunk_ids(path):
    with open(path, "rb") as f:
        return [c.id for c in read_chunks(f)]
