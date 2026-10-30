"""Enough stems in every stem folder (Main.wav does not count)."""

from qabot.report import FAIL, PASS, Result

ID = "stems_count"


def run(ctx):
    need = ctx.rules["stems"]["min_count"]
    if not ctx.export.stem_sets:
        return [Result(ID, FAIL, " ".join(ctx.export.problems) or "No stems folder found.",
                       "Export the stems into a folder called 'Stems Extended' inside the export folder.")]
    out = []
    for s in ctx.export.stem_sets:
        n = len(s.stems)
        ctx.note(s.label, "Stems", n)
        if n < need:
            out.append(Result(ID, FAIL, f"{s.label}: {n} stems, needs at least {need}.",
                              "Export with 'Selected Tracks Only' off / 'All Individual Tracks', "
                              "including the returns."))
        else:
            out.append(Result(ID, PASS, f"{s.label}: {n} stems (at least {need})."))
    return out
