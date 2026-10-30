"""Stems should be named by instrument, not left as Ableton's default names."""

import os
import re

from qabot.report import PASS, WARN, Result
from qabot.checks._util import plural, rel

ID = "files_naming"

DEFAULT_NAME = re.compile(
    r"^(audio|midi|track|inst|instrument|drum rack|simpler|sampler|operator|wavetable|drift|"
    r"analog|meld|serum|serum 2|vital|sylenth1|massive|diva|pigments|spire)?\s*\d*$",
    re.IGNORECASE)
LEADING_NUMBER = re.compile(r"^\d+\s*[-_.)]?\s*")


def _common_prefix(stems):
    """Prefix shared by every stem name, cut back to a word break (Ableton
    puts the export file name in front of each track name)."""
    if len(stems) < 2:
        return ""
    prefix = os.path.commonprefix(stems)
    cut = max(prefix.rfind(" "), prefix.rfind("-"), prefix.rfind("_"))
    return prefix[: cut + 1] if cut >= 0 else ""


def bare_name(stem, prefix=""):
    name = stem[len(prefix):] if prefix and stem.startswith(prefix) else stem
    return LEADING_NUMBER.sub("", name).strip(" -_")


def run(ctx):
    bad = []
    total = 0
    for s in ctx.export.stem_sets:
        prefix = _common_prefix([p.stem for p in s.stems])
        for p in s.stems:
            total += 1
            if DEFAULT_NAME.match(bare_name(p.stem, prefix)):
                bad.append(rel(ctx, p))
    if bad:
        return [Result(ID, WARN, f"{plural(len(bad), 'stem')} still {'has' if len(bad) == 1 else 'have'} "
                                 "a default name instead of an instrument name.",
                       "Rename the tracks in Ableton (Kick, Bass Sub, Arp...) and re-export, "
                       "or rename the files.", files=bad)]
    return [Result(ID, PASS, f"All {total} stems are named by instrument.")]
