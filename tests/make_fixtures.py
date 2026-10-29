"""Fake Ableton exports for testing, made only from test sounds: sine tones,
noise and clicks. No real music, and never Carlos's sale tracks.

    python -m tests.make_fixtures [out_dir]

writes a good export and every broken variant into out_dir (default
test_output/), handy for trying the app without real audio.
"""

import functools
import gzip
import os
import shutil
import struct
import sys
from pathlib import Path

import numpy as np

SR = 44100
STEM_NAMES = [
    "01 Kick", "02 Clap", "03 Hats", "04 Perc", "05 Bass Sub", "06 Bass Mid", "07 Tone A",
    "08 Tone B", "09 Noise Bed", "10 FX Sweep", "A Reverb Short", "B Delay",
]
PUMP_STEMS = ("05 Bass Sub", "06 Bass Mid")


# -- writing -----------------------------------------------------------------
def to_pcm(data, bits):
    full = 2 ** (bits - 1)
    ints = np.clip(np.round(data * full), -full, full - 1).astype(np.int64)
    if bits == 16:
        return ints.astype("<i2").tobytes()
    if bits == 24:
        b = ints.astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3]
        return b.tobytes()
    return ints.astype("<i4").tobytes()


def quantize(data, bits=16):
    full = 2 ** (bits - 1)
    return np.clip(np.round(data * full), -full, full - 1) / full


def write_wav(path, data, rate=SR, bits=16, chunks_before=(), chunks_after=(), float32=False):
    """Plain RIFF writer, so tests control exactly which chunks are in the file."""
    data = np.asarray(data, dtype=np.float64)
    if data.ndim == 1:
        data = data[:, None]
    ch = data.shape[1]
    if float32:
        pcm, bits, tag = data.astype("<f4").tobytes(), 32, 3
    else:
        pcm, tag = to_pcm(data, bits), 1
    align = ch * bits // 8
    fmt = struct.pack("<HHIIHH", tag, ch, rate, rate * align, align, bits)

    def chunk(cid, body):
        return cid.encode("latin-1") + struct.pack("<I", len(body)) + body + (b"\0" if len(body) & 1 else b"")

    body = b"WAVE" + chunk("fmt ", fmt)
    body += b"".join(chunk(c, b) for c, b in chunks_before)
    body += chunk("data", pcm)
    body += b"".join(chunk(c, b) for c, b in chunks_after)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
    return path


def info_chunk(**tags):
    body = b"INFO"
    for k, v in tags.items():
        raw = v.encode() + b"\0"
        body += k.encode() + struct.pack("<I", len(raw)) + raw + (b"\0" if len(raw) & 1 else b"")
    return ("LIST", body)


# -- test sounds ---------------------------------------------------------------
def _beats(n, bpm, rate):
    return np.arange(n) / rate * bpm / 60.0


def pump(n, bpm, rate=SR, depth=0.85, start_bar=None, end_bar=None):
    """Volume dip on every beat, like a sidechain (only between the given bars)."""
    b = _beats(n, bpm, rate)
    env = 1 - depth * np.exp(-(b % 1) / 0.12)
    if start_bar is not None:
        bar = b / 4
        env = np.where((bar >= start_bar) & (bar < end_bar), env, 1.0)
    return env


def stem_sounds(n, bpm, rate=SR, seed=7):
    rng = np.random.default_rng(seed)
    t = np.arange(n) / rate
    b = _beats(n, bpm, rate)
    ph = b % 1
    noise = rng.standard_normal(n)
    hi = np.diff(noise, prepend=0)
    s = {
        "01 Kick": np.sin(2 * np.pi * 50 * t) * np.exp(-ph / 0.06),
        "02 Clap": noise * np.exp(-((b - 1) % 2) / 0.03) * 0.6,
        "03 Hats": hi * np.exp(-((b + 0.5) % 1) / 0.02) * 0.3,
        "04 Perc": (np.abs((b * 4) % 1) < 0.004).astype(float) * 0.8,
        "05 Bass Sub": np.sin(2 * np.pi * 55 * t) * 0.7,
        "06 Bass Mid": sum(np.sin(2 * np.pi * 110 * k * t) / k for k in range(1, 6)) * 0.35,
        "07 Tone A": np.sin(2 * np.pi * 440 * t) * 0.15,
        "08 Tone B": np.sin(2 * np.pi * 660 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.5 * t)) * 0.12,
        "09 Noise Bed": np.convolve(noise, np.ones(8) / 8, mode="same") * 0.1,
        "10 FX Sweep": np.sin(2 * np.pi * (200 + 300 * t / t[-1]) * t) * 0.1,
        "A Reverb Short": np.convolve(rng.standard_normal(n), np.ones(32) / 32, mode="same") * 0.15,
        "B Delay": np.roll((np.abs((b * 2) % 1) < 0.003).astype(float), int(rate * 0.1)) * 0.5,
    }
    out = {}
    for i, (name, x) in enumerate(s.items()):
        pan = 0.5 + 0.3 * np.sin(i * 1.7)
        out[name] = np.stack([x * (1 - pan) * 1.4, x * pan * 1.4], axis=1)
    return out


@functools.lru_cache(maxsize=8)
def master_sound(seconds, lufs=-8.0, peak_db=-1.2, seed=3):
    """Dense noise + tones, soft-clipped to a peak and gained to a loudness."""
    import pyloudnorm
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal((n, 2)) * 0.3 + np.sin(2 * np.pi * 55 * t)[:, None] * 0.5
    meter = pyloudnorm.Meter(SR)
    probe = slice(0, min(n, SR * 10))
    lo, hi = 0.1, 20.0
    ceiling = 10 ** (peak_db / 20)
    for _ in range(25):
        drive = (lo + hi) / 2
        y = np.tanh(drive * x[probe]) / np.tanh(drive * 4) * ceiling
        if meter.integrated_loudness(y) < lufs:
            lo = drive
        else:
            hi = drive
    y = np.tanh(drive * x) / np.tanh(drive * 4) * ceiling
    if meter.integrated_loudness(y[probe]) > lufs + 0.5:   # quieter target than the clip allows
        y *= 10 ** ((lufs - meter.integrated_loudness(y[probe])) / 20)
    y = np.clip(y, -ceiling, ceiling)
    y.flags.writeable = False
    return y


# -- whole export folders --------------------------------------------------------
def make_export(root, title="Test Track", bars=16, bpm=128, n_stems=12,
                extended_seconds=390, radio_seconds=180, master_lufs=-8.0, masters=True,
                missing_pump=False, silent_stem=False, stem_48k=False, stem_24bit=False,
                ref_stem=False, short_stem=False, clip_stem=False, metadata=False, credential=False,
                private_file=False, main=True, shift_main=0, rack_on=False, drop_stem=None,
                main_peak_db=-4.5, als_text=None, default_names=False, master_cache=None):
    """Write '<title> EXPORT' under root and return its path."""
    ex = Path(root) / f"{title} EXPORT"
    stems_dir = ex / "Stems Extended"
    n = int(round(bars * 4 * 60 / bpm * SR))
    sounds = dict(list(stem_sounds(n, bpm).items())[:n_stems])
    total = sum(sounds.values())
    gain = 10 ** (main_peak_db / 20) / np.abs(total).max()
    stems = {k: quantize(v * gain) for k, v in sounds.items()}
    if silent_stem:
        stems["09 Noise Bed"] = np.zeros_like(stems["09 Noise Bed"])

    mix = sum(stems.values())
    if missing_pump:   # the sidechain sat on the bus: Main has the pump, the stems don't
        env = pump(n, bpm, start_bar=8, end_bar=16)[:, None]
        mix = mix + sum(stems[k] * (env - 1) for k in PUMP_STEMS)
    if rack_on:
        mix = np.tanh(mix * 2.5) * 0.6
    if shift_main:
        mix = np.roll(mix, shift_main, axis=0)
    mix = quantize(mix)

    for name, x in stems.items():
        if name == drop_stem:
            continue
        kw = {}
        if metadata and name == "01 Kick":
            kw["chunks_before"] = [info_chunk(IART="Carlos Test", ICMT="made in Ableton"), ("bext", b"\0" * 602)]
        if credential and name == "02 Clap":
            kw["chunks_after"] = [("C2PA", b"jumb" + b"\0" * 60)]
        if stem_24bit and name == "07 Tone A":
            kw["bits"] = 24
        if short_stem and name == "08 Tone B":
            x = x[:-1000]
        if clip_stem and name == "04 Perc":
            x = x.copy()
            x[1000:1005] = 1.0
        if stem_48k and name == "10 FX Sweep":
            write_wav(stems_dir / f"{name}.wav", x, rate=48000)
            continue
        write_wav(stems_dir / f"{name}.wav", x, **kw)
    if default_names:
        write_wav(stems_dir / "13 Audio 12.wav", np.zeros((n, 2)) + 1e-3)
    if ref_stem:
        write_wav(stems_dir / "REF Track.wav", stems["07 Tone A"])
    if main:
        write_wav(stems_dir / "Main.wav", mix)

    if masters:
        mdir = ex / "Masters"
        for label, sec in (("Extended Mix", extended_seconds), ("Radio Mix", radio_seconds)):
            if not sec:
                continue
            dst = mdir / f"{title} ({label}).wav"
            if metadata:
                write_wav(dst, master_sound(sec, master_lufs), chunks_before=[info_chunk(IART="Carlos Test")])
                continue
            # Same master sound is shared between exports through a hard link (saves disk and time).
            cached = Path(master_cache or Path(root) / ".masters") / f"{sec}s {master_lufs:g}.wav"
            if not cached.exists():
                write_wav(cached, master_sound(sec, master_lufs))
            mdir.mkdir(parents=True, exist_ok=True)
            try:
                os.link(cached, dst)
            except OSError:
                shutil.copyfile(cached, dst)
    if private_file:
        (ex / "Splice License.pdf").write_bytes(b"%PDF-1.4 test")
        (ex / "Masters" / "qa notes.md").parent.mkdir(parents=True, exist_ok=True)
        (ex / "Masters" / "qa notes.md").write_text("notes", encoding="utf-8")
    if als_text is not None:
        proj = ex / "Project"
        proj.mkdir(parents=True, exist_ok=True)
        with gzip.open(proj / f"{title}.als", "wb") as f:
            f.write(als_text.encode())
        (proj / "Samples").mkdir(exist_ok=True)
        write_wav(proj / "Samples" / "Imported" / "hit.wav", stems["04 Perc"][:SR])
    return ex


VARIANTS = {
    "Good Track": {},
    "Missing Pump": {"missing_pump": True},
    "Silent Stem": {"silent_stem": True},
    "Wrong Format": {"stem_48k": True, "stem_24bit": True},
    "Ref Stem": {"ref_stem": True},
    "Short Stem": {"short_stem": True},
    "Quiet Master": {"master_lufs": -12.0},
    "Hidden Tags": {"metadata": True, "credential": True},
    "Private Files": {"private_file": True},
}


def main(out_dir=None):
    out = Path(out_dir or Path(__file__).resolve().parent.parent / "test_output")
    for title, kw in VARIANTS.items():
        print("writing", make_export(out, title=title, **kw))
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
