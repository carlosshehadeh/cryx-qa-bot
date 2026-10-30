"""Every stem, Main file and master must be WAV at the profile's rate and bit depth."""

from qabot.audio import FLOAT
from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import plural, rel

ID = "files_format"


def run(ctx):
    rate = ctx.rules["format"]["sample_rate"]
    bits = ctx.rules["format"]["bit_depth"]
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
            kind = f"{info.bit_depth}-bit float" if info.format_tag == FLOAT else f"format {info.format_tag}"
            groups["float"].append(f"{rel(ctx, p)}: {kind}")
        elif info.bit_depth != bits:
            groups["bits"].append(f"{rel(ctx, p)}: {info.bit_depth}-bit")
        if info.sample_rate != rate:
            groups["rate"].append(f"{rel(ctx, p)}: {info.sample_rate / 1000:g} kHz")

    want = f"WAV {rate / 1000:g} kHz/{bits}-bit"
    text = {
        "wav": ("not WAV", "Export as WAV from Ableton (File > Export Audio/Video, File Type WAV)."),
        "broken": ("can't be read", "Re-export these files; they may be cut off or still being written."),
        "float": ("floating point, not PCM", f"In Ableton's export window set Bit Depth to {bits}."),
        "bits": (f"not {bits}-bit", f"In Ableton's export window set Bit Depth to {bits} (dither on)."),
        "rate": (f"not {rate / 1000:g} kHz", f"In Ableton's export window set Sample Rate to {rate}."),
    }
    out = []
    for key, bad in groups.items():
        if bad:
            what, fix = text[key]
            out.append(Result(ID, FAIL, f"{plural(len(bad), 'file')} {'is' if len(bad) == 1 else 'are'} {what}.",
                              fix, files=bad))
    return out or [Result(ID, PASS, f"All {len(files)} files are {want}.")]
