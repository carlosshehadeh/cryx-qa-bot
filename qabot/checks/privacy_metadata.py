"""Hidden chunks in the WAVs (LIST/INFO, bext, iXML, id3, C2PA/JUMBF content credentials).

Not a FAIL: the buyer copies are rewritten with only `fmt ` and `data`.
The report says what was found, so it's clear what gets removed. A
content-credential tag is a WARN: it means the audio went through a tool or
service that stamps its output.
"""

from collections import Counter

from qabot.report import PASS, WARN, Result
from qabot.checks._util import plural, rel

ID = "privacy_metadata"
CREDENTIAL_IDS = {"c2pa", "jumb", "jumd"}
CREDENTIAL_BYTES = (b"c2pa", b"jumb", b"jumd")


def _credential(info):
    if any(c.id.strip().lower() in CREDENTIAL_IDS for c in info.chunks):
        return True
    with open(info.path, "rb") as f:
        for c in info.chunks:
            if c.id in ("fmt ", "data") or c.size > 50_000_000:
                continue
            f.seek(c.offset)
            raw = f.read(c.size).lower()
            if any(b in raw for b in CREDENTIAL_BYTES):
                return True
    return False


def run(ctx):
    wavs = [p for p in ctx.export.all_wavs() if ctx.readable(p)]
    found = {p: ctx.info(p).extra_chunks for p in wavs}
    found = {p: ids for p, ids in found.items() if ids}
    out = []
    stamped = [p for p in found if _credential(ctx.info(p))]
    if stamped:
        out.append(Result(ID, WARN, f"Content-credential (C2PA) tag in {plural(len(stamped), 'file')}.",
                          "The buyer copies drop it, but these files went through a tool or service that "
                          "stamps its output. Make sure they come straight from Ableton.",
                          files=[rel(ctx, p) for p in stamped]))
    if not found:
        out.append(Result(ID, PASS, f"No hidden chunks in {plural(len(wavs), 'WAV')}."))
        return out
    kinds = Counter(c.strip() for ids in found.values() for c in ids)
    summary = ", ".join(f"{k} ({n})" for k, n in kinds.most_common())
    out.append(Result(ID, PASS, f"Hidden chunks found in {plural(len(found), 'file')}: {summary}. "
                                "The buyer copies are rewritten without them.",
                      files=[f"{rel(ctx, p)}: {', '.join(ids)}" for p, ids in found.items()]))
    return out
