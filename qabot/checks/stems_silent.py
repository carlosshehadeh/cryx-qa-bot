"""No empty stems: every stem must have sound somewhere."""

from qabot.report import FAIL, PASS, Result
from qabot.checks._util import names, rel

ID = "stems_silent"


def run(ctx):
    limit = ctx.rules["stems"]["silent_below_dbfs"]
    out = []
    for s in ctx.export.stem_sets:
        stems = [p for p in s.stems if ctx.readable(p)]
        silent = [p for p in stems if ctx.stats(p).peak_db < limit]
        if silent:
            out.append(Result(ID, FAIL, f"{s.label}: {names(silent)} {'is' if len(silent) == 1 else 'are'} silent.",
                              "Delete it, or unmute the track and re-export.",
                              files=[rel(ctx, p) for p in silent]))
        elif stems:
            out.append(Result(ID, PASS, f"{s.label}: no silent stems."))
    return out
