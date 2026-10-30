"""Helper tracks (reference, sidechain trigger, buses, groups) must not be stems."""

from qabot.report import FAIL, PASS, Result
from qabot.checks._util import rel, word_pattern

ID = "stems_forbidden"


def run(ctx):
    words = ctx.rules["stems"]["forbidden_names"]
    patterns = [(w, word_pattern(w)) for w in words]
    bad = []
    for s in ctx.export.stem_sets:
        for p in s.stems:
            hit = next((w for w, rx in patterns if rx.search(p.stem)), None)
            if hit:
                bad.append(f"{rel(ctx, p)} (matches '{hit}')")
    if bad:
        return [Result(ID, FAIL, f"{len(bad)} helper track{'s' if len(bad) > 1 else ''} exported as a stem.",
                       "Delete these files. Buses and groups render without their devices, and REF / "
                       "SC TRIG tracks are not part of the music. Fold their sound into the real stems.",
                       files=bad)]
    return [Result(ID, PASS, "No REF, SC TRIG, bus, group or master tracks among the stems.")]
