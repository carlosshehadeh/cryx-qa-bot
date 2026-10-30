"""The null test: do the stems add up to the unmastered mix (Main.wav)?

1. Add every stem (not Main) sample by sample.
2. Subtract the sum from Main. What's left is the residual.
3. Residual level vs the mix, in dB: PASS at or below pass_db, FAIL above fail_db.
4. If it doesn't pass: try small time offsets, then say where (bars), what
   (stems the residual looks like) and why (likely causes).
"""

import math

import numpy as np

from qabot import audio
from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import rel

ID = "null_test"

HINTS = {
    "bus": "Sidechain or effects on a bus or group: buses render without their devices, so the "
           "stems miss that sound (track one: the bass pump). Move the devices onto the tracks.",
    "rack": "The master rack (CRYX MASTER) was on when Main or the stems were exported. Turn it off "
            "for both and export again.",
    "missing": "A stem is missing: a return (reverb, delay) or a track that wasn't exported.",
    "muted": "A track was muted or soloed in one export and not the other.",
    "returns": "'Include Return and Main Effects' was on for the stems. Turn it off.",
}


def _shifted(x, off):
    """x moved later by off samples (earlier when negative), zero filled."""
    if off == 0:
        return x
    y = np.zeros_like(x)
    if off > 0:
        y[off:] = x[:-off]
    else:
        y[:off] = x[-off:]
    return y


def _fit(x, frames, channels):
    """Stem samples matched to Main's length and channel count."""
    if x.shape[1] != channels:
        x = np.repeat(x.mean(axis=1, keepdims=True), channels, axis=1)
    if x.shape[0] >= frames:
        return x[:frames]
    return np.vstack([x, np.zeros((frames - x.shape[0], channels), dtype=x.dtype)])


def _residual_db(main, total, energy, off):
    r = main - _shifted(total, off)
    return 10 * math.log10(max(float(np.sum(r.astype(np.float64) ** 2)), 1e-30) / energy)


def _best_offset(main, total, rate, max_off):
    """Lag (samples) that lines the stem sum up best with Main, measured on
    the loudest 10 seconds."""
    m, t = audio.mono(main).astype(np.float64), audio.mono(total).astype(np.float64)
    seg = min(len(m) - 2 * max_off, rate * 10)
    if seg <= max_off:
        return 0
    hop = max(1, seg // 2)
    starts = range(max_off, max(max_off + 1, len(m) - seg - max_off), hop)
    start = max(starts, key=lambda s: float(np.dot(m[s:s + seg], m[s:s + seg])))
    ref = m[start:start + seg]
    scores = [float(np.dot(ref, t[start - k:start - k + seg])) for k in range(-max_off, max_off + 1)]
    return int(np.argmax(scores)) - max_off


def _bar_ranges(r, main_energy, rate, bpm, beats, threshold_db):
    """Bar ranges (1-based) where the residual is loud, biggest first."""
    spb = rate * 60.0 / bpm * beats
    nbars = max(1, math.ceil(r.shape[0] / spb))
    per_bar = main_energy / nbars
    energy, flagged = [], []
    for i in range(nbars):
        seg = r[int(i * spb):int((i + 1) * spb)]
        e = float(np.sum(seg.astype(np.float64) ** 2))
        energy.append(e)
        flagged.append(e > 0 and 10 * math.log10(e / per_bar) > threshold_db)
    ranges, start = [], None
    for i, f in enumerate(flagged + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            ranges.append((start + 1, i, sum(energy[start:i])))
            start = None
    ranges.sort(key=lambda x: -x[2])
    return ranges, spb


def _bars_text(ranges):
    parts = [f"bar {a}" if a == b else f"bars {a} to {b}" for a, b, _ in ranges[:3]]
    return ", ".join(parts)


def _corr(a, b):
    d = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    return abs(float(np.dot(a, b))) / d if d > 0 else 0.0


def run(ctx):
    if not ctx.export.stem_sets:
        return [Result(ID, FAIL, "No stems to test.", "Export the stems into 'Stems Extended'.")]
    return [check_set(ctx, s) for s in ctx.export.stem_sets]


def check_set(ctx, s):
    nt = ctx.rules["null_test"]
    label = s.label
    if not s.main or not ctx.readable(s.main):
        return Result(ID, FAIL, f"{label}: no Main.wav, so the stems can't be proven to rebuild the mix.",
                      "In Ableton, export the Main track alone with the master rack off, same render range, "
                      f"and put it in '{s.folder.name}' as 'Main.wav'.")
    stems = [p for p in s.stems if ctx.readable(p)]
    if not stems:
        return Result(ID, FAIL, f"{label}: no readable WAV stems to add up.", "Export the stems as WAV.")
    rate = ctx.info(s.main).sample_rate
    other_rate = [p for p in stems if ctx.info(p).sample_rate != rate]
    if other_rate:
        return Result(ID, FAIL, f"{label}: stems and Main have different sample rates, so they can't be added up.",
                      "Export everything at the same sample rate (see files_format).",
                      files=[rel(ctx, p) for p in other_rate])

    main = audio.load(s.main)
    frames, channels = main.shape
    energy = float(np.sum(main.astype(np.float64) ** 2))
    if energy <= 0:
        return Result(ID, FAIL, f"{label}: Main.wav is silent.", "Re-export the Main track.")
    total = np.zeros_like(main)
    for p in stems:
        total += _fit(audio.load(p), frames, channels)

    off = 0
    residual = _residual_db(main, total, energy, 0)
    if residual > nt["pass_db"]:
        lag = _best_offset(main, total, rate, int(nt["max_offset_samples"]))
        if lag:
            shifted = _residual_db(main, total, energy, lag)
            if shifted < residual:
                off, residual = lag, shifted

    numbers = {"residual_db": round(residual, 1), "offset_samples": off}
    ctx.note(label, "Null test residual", f"{residual:.1f} dB")
    if off:
        ctx.note(label, "Null test offset", f"{off:+d} samples")
    offset_text = (f" The stems are {abs(off)} samples {'early' if off > 0 else 'late'} compared to Main "
                   "(checked with that shift); check plugin delay compensation." if off else "")

    if residual <= nt["pass_db"]:
        return Result(ID, PASS, f"{label}: the stems rebuild the mix (residual {residual:.1f} dB).{offset_text}",
                      numbers=numbers)

    # Where, what and why.
    r = main - _shifted(total, off)
    ranges, spb = _bar_ranges(r, energy, rate, ctx.bpm, int(nt.get("beats_per_bar", 4)), nt["pass_db"])
    region = np.zeros(frames, dtype=bool)
    for a, b, _ in ranges[:3]:
        region[int((a - 1) * spb):int(b * spb)] = True
    if not region.any():
        region[:] = True
    rm = audio.mono(r)[region].astype(np.float64)
    scores = []
    for p in stems:
        sm = audio.mono(_shifted(_fit(audio.load(p), frames, channels), off))[region].astype(np.float64)
        scores.append((_corr(rm, sm), p))
    scores.sort(key=lambda x: -x[0])
    top = scores[0][0] if scores else 0.0
    suspects = [p for c, p in scores[:3] if c >= 0.2 and c >= 0.5 * top]
    mix_corr = _corr(rm, audio.mono(_shifted(total, off))[region].astype(np.float64))

    if mix_corr >= 0.9 and mix_corr > top:
        order = ["rack", "returns", "bus", "missing", "muted"]
        suspects = []
    elif not suspects:
        order = ["missing", "muted", "bus", "returns", "rack"]
    else:
        order = ["bus", "muted", "returns", "missing", "rack"]

    where = _bars_text(ranges)
    what = ", ".join(f"'{p.stem}'" for p in suspects)
    msg = f"{label}: the stems don't rebuild the mix (residual {residual:.1f} dB)."
    if where:
        msg += f" Biggest difference: {where} at {ctx.bpm:g} BPM."
    if suspects:
        msg += f" Most likely: {what}."
    elif mix_corr >= 0.9:
        msg += " The difference sounds like the whole mix."
    else:
        msg += " The difference doesn't match any stem."
    msg += offset_text
    fix = "Likely causes: " + " ".join(f"{i}) {HINTS[k]}" for i, k in enumerate(order, 1))
    numbers.update({"bars": where, "suspects": {p.stem: round(c, 2) for c, p in scores[:5]},
                    "mix_correlation": round(mix_corr, 2)})
    level = FAIL if residual > nt["fail_db"] else WARN
    return Result(ID, level, msg, fix, files=[rel(ctx, p) for p in suspects], numbers=numbers)
