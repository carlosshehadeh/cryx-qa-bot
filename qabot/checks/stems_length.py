"""Every stem (and Main) must cover the whole track: same length to the sample."""

from collections import Counter

from qabot.audio import fmt_time
from qabot.report import FAIL, PASS, Result
from qabot.checks._util import rel

ID = "stems_length"


def run(ctx):
    allowed = ctx.rules["stems"]["max_length_diff_samples"]
    out = []
    for s in ctx.export.stem_sets:
        files = [p for p in s.stems + ([s.main] if s.main else []) if ctx.readable(p)]
        if not files:
            continue
        frames = {p: ctx.info(p).frames for p in files}
        usual = Counter(frames.values()).most_common(1)[0][0]
        rate = ctx.info(files[0]).sample_rate
        ctx.note(s.label, "Length", f"{fmt_time(usual / rate)} ({usual} samples)")
        if max(frames.values()) - min(frames.values()) <= allowed:
            out.append(Result(ID, PASS, f"{s.label}: all stems are the same length ({fmt_time(usual / rate)})."))
            continue
        odd = [p for p in files if abs(frames[p] - usual) > allowed]
        out.append(Result(
            ID, FAIL, f"{s.label}: {len(odd)} of {len(files)} files differ in length from the rest.",
            "Export all stems in one go with the same render range (loop brace or selection).",
            files=[f"{rel(ctx, p)}: {frames[p] - usual:+d} samples ({fmt_time(frames[p] / rate)})" for p in odd]))
    return out
