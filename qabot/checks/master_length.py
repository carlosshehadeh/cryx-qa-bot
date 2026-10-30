"""Master length inside the profile's limits; the extended mix near the genre's plan."""

from qabot.audio import fmt_time
from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import masters

ID = "master_length"


def run(ctx):
    r = ctx.rules["master"]
    lo, hi = r["length_min_seconds"], r["length_max_seconds"]
    plan, tol = r.get("plan_extended_seconds"), r.get("plan_tolerance_seconds", 45)
    out = []
    for label, p in masters(ctx):
        sec = ctx.info(p).seconds
        ctx.note("Masters", f"{label} length", fmt_time(sec))
        if not lo <= sec <= hi:
            out.append(Result(ID, FAIL, f"{label}: {fmt_time(sec)} long, needs {fmt_time(lo)} to {fmt_time(hi)}.",
                              "Check the render range in Ableton's export window.", numbers={"seconds": round(sec, 2)}))
        elif label == "Extended Mix" and plan and abs(sec - plan) > tol:
            out.append(Result(ID, WARN, f"{label}: {fmt_time(sec)}, the plan for this genre is about {fmt_time(plan)}.",
                              "Fine if on purpose. Otherwise check the arrangement or the render range.",
                              numbers={"seconds": round(sec, 2)}))
        else:
            out.append(Result(ID, PASS, f"{label}: {fmt_time(sec)} long.", numbers={"seconds": round(sec, 2)}))
    return out
