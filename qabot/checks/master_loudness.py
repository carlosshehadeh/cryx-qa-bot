"""Masters must sit in the profile's integrated loudness range (ITU BS.1770, like Youlean).

lufs_min / lufs_max set to null means the website sets no limit on that side;
both null and the loudness is only measured and noted.
"""

from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import inside, masters, span

ID = "master_loudness"


def run(ctx):
    lo, hi = ctx.rules["master"].get("lufs_min"), ctx.rules["master"].get("lufs_max")
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
        if lo is None and hi is None:
            out.append(Result(ID, PASS, f"{text}. This website sets no LUFS range.", numbers=nums))
        elif inside(m["lufs"], lo, hi):
            out.append(Result(ID, PASS, f"{text}, inside {span(lo, hi)}.", numbers=nums))
        else:
            way = "too quiet" if lo is not None and m["lufs"] < lo else "too loud"
            out.append(Result(ID, FAIL, f"{text}: {way}, needs {span(lo, hi, 'LUFS')}.",
                              "Adjust the gain into the limiter on the master rack and re-export the master.",
                              numbers=nums))
    return out
