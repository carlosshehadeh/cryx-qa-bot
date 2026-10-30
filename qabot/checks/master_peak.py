"""Master peak inside the site's range (true peak or sample peak, from the rules)."""

from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import masters

ID = "master_peak"


def run(ctx):
    r = ctx.rules["master"]
    lo, hi = r.get("peak_min_db"), r.get("peak_max_db")
    true_peak = r.get("peak_measure", "true_peak") == "true_peak"
    unit = "dBTP" if true_peak else "dBFS"
    span = f"{lo:g} to {hi:g} {unit}" if lo is not None else f"{hi:g} {unit} or lower"
    confirmed = r.get("peak_confirmed", True)
    out = []
    for label, p in masters(ctx):
        m = ctx.master(p)
        peak = m["true_peak"] if true_peak else m["sample_peak"]
        ctx.note("Masters", f"{label} peak", f"{m['true_peak']:.2f} dBTP true peak, "
                                             f"{m['sample_peak']:.2f} dBFS sample peak")
        nums = {"true_peak_dbtp": round(m["true_peak"], 2), "sample_peak_dbfs": round(m["sample_peak"], 2)}
        if (lo is None or peak >= lo) and (hi is None or peak <= hi):
            out.append(Result(ID, PASS, f"{label}: peak {peak:.2f} {unit}, inside {span}.", numbers=nums))
            continue
        msg = f"{label}: peak {peak:.2f} {unit}, needs {span}."
        target = hi - 0.1 if lo is None else (lo + hi) / 2
        fix = f"Set the limiter ceiling on the master rack to about {target:.1f} dB (true peak), then re-export."
        if not confirmed:
            msg += " (Peak rule not confirmed yet, so only a warning.)"
        out.append(Result(ID, FAIL if confirmed else WARN, msg, fix, numbers=nums))
    return out
