"""320 kbps CBR MP3 from a master WAV, with the LAME encoder (lameenc).

No ffmpeg needed. The MP3 carries no tags (no title, no artist, nothing).
"""

from pathlib import Path

import numpy as np

from qabot import audio


def to_int16(data):
    """float -1..1 to 16-bit samples (exact for 16-bit masters)."""
    return np.clip(np.round(data * 32768.0), -32768, 32767).astype(np.int16)


def encode(src, dst, bitrate=320):
    import lameenc
    info = audio.read_info(src)
    if not info.ok:
        raise ValueError(f"{Path(src).name}: {info.error}")
    data = audio.load(src)
    if data.shape[1] > 2:
        data = data[:, :2]
    pcm = to_int16(data)
    enc = lameenc.Encoder()
    enc.set_bit_rate(int(bitrate))
    enc.set_in_sample_rate(info.sample_rate)
    enc.set_channels(pcm.shape[1])
    enc.set_quality(2)   # 2 = high quality, 7 = fast
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    with open(tmp, "wb") as out:
        step = 1 << 16
        for i in range(0, pcm.shape[0], step):
            out.write(enc.encode(pcm[i:i + step].tobytes()))
        out.write(enc.flush())
    tmp.replace(dst)
    return dst


# -- reading back (for tests and the final check) --------------------------
BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
RATES = {0: 44100, 1: 48000, 2: 32000}


def frames(path):
    """(number of MPEG-1 Layer III frames, set of bitrates, sample rate)."""
    raw = Path(path).read_bytes()
    pos, count, rates, sr = 0, 0, set(), 0
    if raw[:3] == b"ID3":
        pos = 10 + ((raw[6] << 21) | (raw[7] << 14) | (raw[8] << 7) | raw[9])
    while pos + 4 <= len(raw):
        h = int.from_bytes(raw[pos:pos + 4], "big")
        if (h >> 21) & 0x7FF != 0x7FF or (h >> 19) & 3 != 3 or (h >> 17) & 3 != 1:
            pos += 1
            continue
        br = BITRATES[(h >> 12) & 0xF] if (h >> 12) & 0xF < 15 else 0
        sr = RATES.get((h >> 10) & 3, 0)
        if not br or not sr:
            pos += 1
            continue
        size = 144000 * br // sr + ((h >> 9) & 1)
        rates.add(br)
        count += 1
        pos += size
    return count, rates, sr
