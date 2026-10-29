"""The unmastered mix (Main.wav) should peak between the profile's limits (-3 to -6 dBFS)."""

from qabot.report import FAIL, PASS, WARN, Result

ID = "mix_headroom"


def run(ctx):
    hi = ctx.rules["mix"]["peak_max_dbfs"]
    lo = ctx.rules["mix"]["peak_min_dbfs"]
    out = []
    for s in ctx.export.stem_sets:
        if not s.main or not ctx.readable(s.main):
            out.append(Result(ID, WARN, f"{s.label}: no readable Main.wav, so the headroom can't be checked.",
                              "Export the Main track with the master rack off (see null_test)."))
            continue
        peak = ctx.stats(s.main).peak_db
        ctx.note(s.label, "Main.wav peak", f"{peak:.1f} dBFS")
        if peak > hi:
            out.append(Result(ID, FAIL, f"{s.label}: Main peaks at {peak:.1f} dBFS, above {hi:g}.",
                              f"Lower the master fader (rack off) so the mix peaks between {lo:g} and {hi:g} dBFS, "
                              "then re-export stems and Main.", numbers={"peak_dbfs": round(peak, 2)}))
        elif peak < lo:
            out.append(Result(ID, WARN, f"{s.label}: Main peaks at {peak:.1f} dBFS, below {lo:g}.",
                              f"A bit quiet. Aim for a peak between {lo:g} and {hi:g} dBFS.",
                              numbers={"peak_dbfs": round(peak, 2)}))
        else:
            out.append(Result(ID, PASS, f"{s.label}: Main peaks at {peak:.1f} dBFS ({lo:g} to {hi:g}).",
                              numbers={"peak_dbfs": round(peak, 2)}))
    return out
