"""Reading WAV files and measuring them.

- `read_info`: the RIFF chunk list and the format (rate, bit depth, length),
  read straight from the file header, so hidden chunks are seen exactly.
- `load`: the samples as float32, shape (frames, channels).
- `stats`: sample peak, full-scale (clipped) samples and the longest run.
- `true_peak_db`: 4x oversampled peak, like a true peak meter.
- `loudness`: integrated LUFS (ITU BS.1770 via pyloudnorm) and short-term max.
"""

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".ogg", ".m4a"}
PCM, FLOAT, EXTENSIBLE = 1, 3, 0xFFFE
SILENCE_DB = -200.0


def db(x):
    return 20 * math.log10(x) if x > 0 else SILENCE_DB


@dataclass
class Chunk:
    id: str
    offset: int      # where the chunk's data starts
    size: int


@dataclass
class WavInfo:
    path: Path
    ok: bool = False
    error: str = ""
    format_tag: int = 0
    channels: int = 0
    sample_rate: int = 0
    bit_depth: int = 0
    frames: int = 0
    chunks: list = field(default_factory=list)

    @property
    def is_pcm(self):
        return self.format_tag == PCM

    @property
    def seconds(self):
        return self.frames / self.sample_rate if self.sample_rate else 0.0

    @property
    def extra_chunks(self):
        """Every chunk that is not audio format or audio data."""
        return [c.id for c in self.chunks if c.id not in ("fmt ", "data")]

    def chunk(self, cid):
        return next((c for c in self.chunks if c.id == cid), None)


def read_chunks(f):
    """Walk the RIFF chunks of an open WAV file."""
    head = f.read(12)
    if len(head) < 12 or head[8:12] != b"WAVE":
        raise ValueError("not a WAV file")
    if head[:4] != b"RIFF":
        raise ValueError(f"{head[:4].decode('latin-1')} WAV files are not supported (over 4 GB?)")
    chunks = []
    pos = 12
    while True:
        f.seek(pos)
        h = f.read(8)
        if len(h) < 8:
            break
        cid = h[:4].decode("latin-1")
        size = struct.unpack("<I", h[4:])[0]
        chunks.append(Chunk(cid, pos + 8, size))
        pos += 8 + size + (size & 1)
    return chunks


def read_info(path) -> WavInfo:
    info = WavInfo(Path(path))
    try:
        with open(path, "rb") as f:
            info.chunks = read_chunks(f)
            fmt = info.chunk("fmt ")
            data = info.chunk("data")
            if not fmt or not data:
                raise ValueError("no audio in this WAV (fmt or data chunk missing)")
            f.seek(fmt.offset)
            raw = f.read(fmt.size)
        tag, ch, rate, _, align, bits = struct.unpack("<HHIIHH", raw[:16])
        if tag == EXTENSIBLE and len(raw) >= 26:
            tag = struct.unpack("<H", raw[24:26])[0]
        info.format_tag, info.channels, info.sample_rate, info.bit_depth = tag, ch, rate, bits
        file_size = Path(path).stat().st_size
        data_bytes = min(data.size, max(0, file_size - data.offset))
        info.frames = data_bytes // align if align else 0
        info.ok = True
    except (OSError, ValueError, struct.error) as e:
        info.error = str(e)
    return info


def load(path):
    """Samples as float32 in -1..1, shape (frames, channels)."""
    import soundfile as sf
    data, _ = sf.read(str(path), dtype="float32", always_2d=True)
    return data


def full_scale(bit_depth, is_float=False):
    """The largest sample value a file can hold, as a float."""
    if is_float or not bit_depth:
        return 1.0
    return (2 ** (bit_depth - 1) - 1) / 2 ** (bit_depth - 1)


def longest_run(mask):
    """Longest run of True in a 1-D boolean array."""
    if not mask.any():
        return 0
    padded = np.concatenate(([False], mask, [False])).astype(np.int8)
    d = np.diff(padded)
    return int((np.flatnonzero(d == -1) - np.flatnonzero(d == 1)).max())


@dataclass
class Stats:
    peak: float           # linear, 0..1
    clipped: int          # samples at full scale
    clip_run: int         # longest run of full-scale samples in one channel

    @property
    def peak_db(self):
        return db(self.peak)


def stats(data, info=None):
    a = np.abs(data)
    peak = float(a.max()) if a.size else 0.0
    limit = full_scale(info.bit_depth if info else 16, bool(info and info.format_tag == FLOAT))
    hot = a >= limit - 1e-7
    clipped = int(hot.sum())
    run = max((longest_run(hot[:, c]) for c in range(hot.shape[1])), default=0) if clipped else 0
    return Stats(peak, clipped, run)


def true_peak_db(data, oversample=4, block=1 << 18, pad=256):
    """4x oversampled peak in dBTP, worked through in blocks to save memory."""
    from scipy.signal import resample_poly
    peak = 0.0
    n = data.shape[0]
    for c in range(data.shape[1]):
        x = data[:, c].astype(np.float64)
        for start in range(0, n, block):
            lo, hi = max(0, start - pad), min(n, start + block + pad)
            y = resample_poly(x[lo:hi], oversample, 1)
            a, b = (start - lo) * oversample, (min(n, start + block) - lo) * oversample
            peak = max(peak, float(np.abs(y[a:b]).max()) if b > a else 0.0)
    return db(peak)


def _k_weighted(x, rate):
    """BS.1770 K-weighting, using pyloudnorm's filter stages."""
    import pyloudnorm
    y = x.astype(np.float64)
    for stage in pyloudnorm.Meter(rate)._filters.values():
        for c in range(y.shape[1]):
            y[:, c] = stage.apply_filter(y[:, c])
    return y


def _window_power(y, rate, seconds, hop_seconds=0.1):
    """Mean power (summed over channels) of each window, one every hop."""
    win, hop = int(round(seconds * rate)), int(round(hop_seconds * rate))
    if y.shape[0] < win:
        return np.zeros(0)
    csum = np.concatenate([[0.0], np.cumsum((y ** 2).sum(axis=1))])
    starts = np.arange(0, y.shape[0] - win + 1, hop)
    return (csum[starts + win] - csum[starts]) / win


def _lufs(power):
    with np.errstate(divide="ignore"):
        return -0.691 + 10 * np.log10(power)


def loudness(data, rate):
    """(integrated LUFS, short-term max LUFS), ITU BS.1770-4 with pyloudnorm's
    K-weighting filters. Integrated: 400 ms blocks, 75 % overlap, -70 LUFS
    absolute and -10 LU relative gates. Short-term: 3 s window every 100 ms,
    like Youlean's short-term read-out."""
    y = _k_weighted(data, rate)
    blocks = _window_power(y, rate, 0.4)
    if not blocks.size:
        return SILENCE_DB, SILENCE_DB
    gated = blocks[_lufs(blocks) >= -70.0]
    if not gated.size:
        return SILENCE_DB, SILENCE_DB
    relative = _lufs(gated.mean()) - 10.0
    gated = gated[_lufs(gated) >= relative]
    integrated = float(_lufs(gated.mean()))
    short = _window_power(y, rate, 3.0)
    short_max = float(_lufs(short.max())) if short.size and short.max() > 0 else SILENCE_DB
    return integrated, short_max


def mono(data):
    return data.mean(axis=1) if data.ndim == 2 else data


def fmt_time(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"
