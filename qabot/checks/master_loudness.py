"""Masters must sit in the profile's integrated loudness range (ITU BS.1770, like Youlean)."""

from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import masters

ID = "master_loudness"


def run(ctx):
    lo, hi = ctx.rules["master"]["lufs_min"], ctx.rules["master"]["lufs_max"]
    found = masters(ctx)
    if not found:
        return [Result(ID, WARN, "No master WAV to measure.", "See mixes_present.")]
    out = []
    for label, p in found:
        m = ctx.master(p)
        ctx.note("Masters", f"{label} loudness", f"{m['lufs']:.1f} LUFS integrated, "
                                                 f"short-term max {m['short_max']:.1f} LUFS")
        nums = {"integrated_lufs": round(m["lufs"], 1), "short_term_max_lufs": round(m["short_max"], 1)}
        text = f"{label}: {m['lufs']:.1f} LUFS integrated (short-term max {m['short_max']:.1f})"
        if lo <= m["lufs"] <= hi:
            out.append(Result(ID, PASS, f"{text}, inside {lo:g} to {hi:g}.", numbers=nums))
        else:
            way = "too quiet" if m["lufs"] < lo else "too loud"
            out.append(Result(ID, FAIL, f"{text}: {way}, needs {lo:g} to {hi:g} LUFS.",
                              "Adjust the gain into the limiter on the master rack and re-export the master.",
                              numbers=nums))
    return out
