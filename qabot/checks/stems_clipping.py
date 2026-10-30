"""No stem may hit full scale (0 dBFS): several samples in a row = a clipped render."""

from qabot.report import FAIL, PASS, Result
from qabot.checks._util import rel

ID = "stems_clipping"


def run(ctx):
    out = []
    for s in ctx.export.stem_sets:
        stems = [p for p in s.stems if ctx.readable(p)]
        bad = []
        for p in stems:
            st = ctx.stats(p)
            if st.clipped:
                bad.append(f"{rel(ctx, p)}: {st.clipped} samples at 0 dBFS, longest run {st.clip_run}")
        if bad:
            out.append(Result(ID, FAIL, f"{s.label}: {len(bad)} stem{'s' if len(bad) > 1 else ''} hit 0 dBFS.",
                              "Turn those tracks down (or lower the master fader) and re-export all stems.",
                              files=bad))
        elif stems:
            out.append(Result(ID, PASS, f"{s.label}: no stem hits 0 dBFS."))
    return out
