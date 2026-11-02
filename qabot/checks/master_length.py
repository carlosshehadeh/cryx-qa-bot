"""Master lengths inside the site's limits; the extended mix near the genre's plan."""

from qabot.audio import fmt_time
from qabot.report import PASS, WARN, Result
from qabot.checks._util import MIX_LABEL

ID = "master_length"


def run(ctx):
    r = ctx.rules["length"]
    plan, tol = r.get("plan_extended_seconds"), r.get("plan_tolerance_seconds", 45)
    found = [(k, p) for k, p in ctx.export.masters.items() if ctx.readable(p)]
    found += [(None, p) for p in ctx.export.unknown_masters if ctx.readable(p)]
    out = []
    for kind, p in found:
        label = MIX_LABEL.get(kind, p.stem)
        sec = ctx.info(p).seconds
        ctx.note("Masters", f"{label} length", fmt_time(sec))
        nums = {"seconds": round(sec, 2)}
        limits = r.get(kind.lower()) if kind else r.get("extended")
        lo, hi, level = limits["min"], limits["max"], limits.get("level", "FAIL")
        if not lo <= sec <= hi:
            out.append(Result(ID, level, f"{label}: {fmt_time(sec)} long, this site wants "
                                         f"{fmt_time(lo)} to {fmt_time(hi)}.",
                              "Check the arrangement or the render range in Ableton's export window.", numbers=nums))
        elif kind == "Extended" and plan and abs(sec - plan) > tol:
            out.append(Result(ID, WARN, f"{label}: {fmt_time(sec)}, the plan for this genre is about {fmt_time(plan)}.",
                              "Fine if on purpose. Otherwise check the arrangement or the render range.",
                              numbers=nums))
        else:
            out.append(Result(ID, PASS, f"{label}: {fmt_time(sec)} long.", numbers=nums))
    return out
