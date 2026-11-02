"""Every stem, unmastered mix and master must be WAV at a sample rate and bit
depth the site accepts (stems and mixes can have different rules)."""

from qabot.audio import FLOAT
from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import plural, rel

ID = "files_format"


def _list(values):
    return "/".join(f"{v:g}" for v in values)


def run(ctx):
    fmt = ctx.rules["format"]
    rates = fmt["sample_rates"]
    depth = {"stem": fmt["stem_bit_depths"], "mix": fmt["master_bit_depths"]}
    files = [(p, "mix") for p in list(ctx.export.masters.values()) + ctx.export.unknown_masters]
    for s in ctx.export.stem_sets:
        files += [(p, "stem") for p in s.stems]
    files += [(p, "mix") for p in ctx.export.unmastered.values()]
    if not files:
        return [Result(ID, WARN, "No audio files found to check.",
                       "Export into the 'Masters' and 'Stems Extended' folders (see README).")]

    groups = {"wav": [], "broken": [], "float": [], "bits": [], "rate": []}
    for p, role in files:
        if p.suffix.lower() not in (".wav", ".wave"):
            groups["wav"].append(f"{rel(ctx, p)} ({p.suffix.lstrip('.').upper()})")
            continue
        info = ctx.info(p)
        if not info.ok:
            groups["broken"].append(f"{rel(ctx, p)}: {info.error}")
            continue
        float_ok = info.format_tag == FLOAT and info.bit_depth == 32 and 32 in depth[role]
        if not info.is_pcm and not float_ok:
            kind = f"{info.bit_depth}-bit float" if info.format_tag == FLOAT else f"format {info.format_tag}"
            groups["float"].append(f"{rel(ctx, p)}: {kind}")
        elif info.bit_depth not in depth[role]:
            groups["bits"].append(f"{rel(ctx, p)}: {info.bit_depth}-bit, needs {_list(depth[role])}-bit")
        if info.sample_rate not in rates:
            groups["rate"].append(f"{rel(ctx, p)}: {info.sample_rate / 1000:g} kHz")

    want_rate = " or ".join(f"{r / 1000:g} kHz" for r in rates)
    text = {
        "wav": ("not WAV", "Export as WAV from Ableton (File > Export Audio/Video, File Type WAV)."),
        "broken": ("can't be read", "Re-export these files; they may be cut off or still being written."),
        "float": ("in a format this site doesn't take",
                  f"In Ableton's export window set Bit Depth to {_list(depth['stem'])}."),
        "bits": ("at the wrong bit depth",
                 f"In Ableton's export window set Bit Depth: stems {_list(depth['stem'])}, "
                 f"masters and mixdowns {_list(depth['mix'])} (dither on when going to 16)."),
        "rate": (f"not {want_rate}", f"In Ableton's export window set Sample Rate to {rates[0]}."),
    }
    out = []
    for key, bad in groups.items():
        if bad:
            what, fix = text[key]
            out.append(Result(ID, FAIL, f"{plural(len(bad), 'file')} {'is' if len(bad) == 1 else 'are'} {what}.",
                              fix, files=bad))
    return out or [Result(ID, PASS, f"All {len(files)} files are WAV at {want_rate}, stems "
                                    f"{_list(depth['stem'])}-bit, masters {_list(depth['mix'])}-bit.")]
