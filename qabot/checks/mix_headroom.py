"""Unmastered mixes (master chain off) must peak inside the site's range, and
on some sites all versions must peak at the same level."""

from qabot.checks._util import MIX_LABEL
from qabot.report import FAIL, PASS, WARN, Result

ID = "mix_headroom"


def _peak(ctx, path, measure):
    if measure == "true_peak":
        return ctx.master(path)["true_peak"], "dBTP true peak"
    return ctx.stats(path).peak_db, "dBFS"


def run(ctx):
    r = ctx.rules["mix"]
    lo, hi = r.get("peak_min_db"), r.get("peak_max_db")
    measure = r.get("peak_measure", "sample_peak")
    mixes = {k: p for k, p in ctx.export.unmastered.items() if ctx.readable(p)}
    if not mixes:
        return [Result(ID, WARN, "No readable unmastered mix (Main.wav), so the headroom can't be checked.",
                       "Export the Main track with the master rack off into 'Stems Extended' as 'Main.wav'.")]
    out, peaks = [], {}
    for kind, p in mixes.items():
        label = f"{MIX_LABEL.get(kind, kind)} unmastered"
        peak, unit = _peak(ctx, p, measure)
        peaks[kind] = peak
        ctx.note("Unmastered", f"{label} peak", f"{peak:.1f} {unit}")
        nums = {"peak": round(peak, 2), "measure": unit}
        if hi is not None and peak > hi:
            span = f"{lo:g} to {hi:g}" if lo is not None else f"{hi:g} or lower"
            out.append(Result(ID, FAIL, f"{label}: peaks at {peak:.1f} {unit}, above {hi:g}.",
                              f"Lower the master fader (rack off) so the mix peaks at {span}, "
                              "then re-export stems and Main.", numbers=nums))
        elif lo is not None and peak < lo:
            out.append(Result(ID, WARN, f"{label}: peaks at {peak:.1f} {unit}, below {lo:g}.",
                              f"A bit quiet. Aim for {lo:g} to {hi:g}.", numbers=nums))
        else:
            rule = ("no headroom rule on this site" if lo is None and hi is None else
                    f"{lo:g} to {hi:g}" if lo is not None else f"{hi:g} or lower")
            out.append(Result(ID, PASS, f"{label}: peaks at {peak:.1f} {unit} ({rule}).", numbers=nums))
    tol = r.get("same_peak_tolerance_db")
    if tol is not None and len(peaks) > 1 and max(peaks.values()) - min(peaks.values()) > tol:
        out.append(Result(ID, WARN, "The unmastered versions don't peak at the same level: "
                          + ", ".join(f"{MIX_LABEL.get(k, k)} {v:.1f}" for k, v in peaks.items()) + ".",
                          "This site wants every unmastered version at the same peak. Use the same fader setting."))
    return out
