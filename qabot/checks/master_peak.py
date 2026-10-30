"""Master peak inside the profile's range (true peak or sample peak, from the rules)."""

from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import inside, masters, span

ID = "master_peak"


def run(ctx):
    r = ctx.rules["master"]
    lo, hi = r.get("peak_min_db"), r.get("peak_max_db")
    true_peak = r.get("peak_measure", "true_peak") == "true_peak"
    unit = "dBTP" if true_peak else "dBFS"
    confirmed = r.get("peak_confirmed", True)
    out = []
    for label, p in masters(ctx):
        m = ctx.master(p)
        peak = m["true_peak"] if true_peak else m["sample_peak"]
        ctx.note("Masters", f"{label} peak", f"{m['true_peak']:.2f} dBTP true peak, "
                                             f"{m['sample_peak']:.2f} dBFS sample peak")
        nums = {"true_peak_dbtp": round(m["true_peak"], 2), "sample_peak_dbfs": round(m["sample_peak"], 2)}
        if inside(peak, lo, hi):
            out.append(Result(ID, PASS, f"{label}: peak {peak:.2f} {unit}, inside {span(lo, hi)}.", numbers=nums))
            continue
        msg = f"{label}: peak {peak:.2f} {unit}, needs {span(lo, hi, unit)}."
        fix = "Set the limiter ceiling on the master rack to land inside the range, then re-export."
        if not confirmed:
            msg += " (Peak rule not confirmed yet, so only a warning.)"
            fix = (f"Check {ctx.rules.get('marketplace', 'the website')}'s seller guidelines for the master peak and set it in the rules file "
                   "(master peak_min_db / peak_max_db, then peak_confirmed: true). " + fix)
        out.append(Result(ID, FAIL if confirmed else WARN, msg, fix, numbers=nums))
    return out
