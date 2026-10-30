"""Every stem, Main file and master must be WAV at the profile's rate and bit depth.

sample_rate and bit_depth can each be one number or a list of allowed ones.
32-bit float only passes when the profile sets allow_float and lists 32.
"""

from qabot.audio import FLOAT
from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import plural, rel

ID = "files_format"


def run(ctx):
    fmt = ctx.rules["format"]
    rates, bitss = _allowed(fmt["sample_rate"]), _allowed(fmt["bit_depth"])
    allow_float = fmt.get("allow_float", False)
    files = list(ctx.export.masters.values()) + ctx.export.unknown_masters
    for s in ctx.export.stem_sets:
        files += s.stems + ([s.main] if s.main else [])
    if not files:
        return [Result(ID, WARN, "No audio files found to check.",
                       "Export into the 'Masters' and 'Stems Extended' folders (see README).")]

    groups = {"wav": [], "broken": [], "float": [], "rate": [], "bits": []}
    for p in files:
        if p.suffix.lower() not in (".wav", ".wave"):
            groups["wav"].append(f"{rel(ctx, p)} ({p.suffix.lstrip('.').upper()})")
            continue
        info = ctx.info(p)
        if not info.ok:
            groups["broken"].append(f"{rel(ctx, p)}: {info.error}")
            continue
        if not info.is_pcm:
            if not (allow_float and info.format_tag == FLOAT and info.bit_depth in bitss):
                kind = f"{info.bit_depth}-bit float" if info.format_tag == FLOAT else f"format {info.format_tag}"
                groups["float"].append(f"{rel(ctx, p)}: {kind}")
        elif info.bit_depth not in bitss:
            groups["bits"].append(f"{rel(ctx, p)}: {info.bit_depth}-bit")
        if info.sample_rate not in rates:
            groups["rate"].append(f"{rel(ctx, p)}: {info.sample_rate / 1000:g} kHz")

    rate_text = " or ".join(f"{r / 1000:g}" for r in rates) + " kHz"
    bits_text = " or ".join(str(b) for b in bitss) + "-bit"
    pcm_bits = " or ".join(str(b) for b in bitss if b != 32 or not allow_float) or str(bitss[0])
    want = f"WAV {rate_text}/{bits_text}"
    text = {
        "wav": ("not WAV", "Export as WAV from Ableton (File > Export Audio/Video, File Type WAV)."),
        "broken": ("can't be read", "Re-export these files; they may be cut off or still being written."),
        "float": ("floating point, not PCM", f"In Ableton's export window set Bit Depth to {pcm_bits}."),
        "bits": (f"not {bits_text}", f"In Ableton's export window set Bit Depth to {pcm_bits} (dither on)."),
        "rate": (f"not {rate_text}", f"In Ableton's export window set Sample Rate to {rates[0]}."),
    }
    out = []
    for key, bad in groups.items():
        if bad:
            what, fix = text[key]
            out.append(Result(ID, FAIL, f"{plural(len(bad), 'file')} {'is' if len(bad) == 1 else 'are'} {what}.",
                              fix, files=bad))
    return out or [Result(ID, PASS, f"All {len(files)} files are {want}.")]


def _allowed(value):
    return list(value) if isinstance(value, (list, tuple)) else [value]
