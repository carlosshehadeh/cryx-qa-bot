"""Small helpers shared by the checks."""

import re

MIX_LABEL = {"Extended": "Extended Mix", "Radio": "Radio Mix"}


def rel(ctx, path):
    """Path as Carlos sees it inside the export folder: 'Stems Extended/01 Kick.wav'."""
    try:
        return path.relative_to(ctx.export.root).as_posix()
    except ValueError:
        return str(path)


def plural(n, word, many=None):
    return f"{n} {word if n == 1 else (many or word + 's')}"


def names(paths, limit=4):
    shown = ", ".join(f"'{p.name}'" for p in paths[:limit])
    return shown + (f" and {len(paths) - limit} more" if len(paths) > limit else "")


def masters(ctx):
    """(label, path) for every master WAV we can measure."""
    out = [(MIX_LABEL.get(k, k), p) for k, p in ctx.export.masters.items()]
    out += [(p.stem, p) for p in ctx.export.unknown_masters]
    return [(label, p) for label, p in out if ctx.readable(p)]


def word_pattern(word):
    """Whole-word match, ignoring case; spaces in the word also match '-', '_' or nothing."""
    parts = [re.escape(w) for w in word.split()]
    return re.compile(r"(?<![a-z])" + r"[\s_-]*".join(parts) + r"(?![a-z])", re.IGNORECASE)


def inside(value, lo, hi):
    """lo <= value <= hi, where a missing (None) limit is no limit."""
    return (lo is None or value >= lo) and (hi is None or value <= hi)


def span(lo, hi, unit=""):
    """'-9 to -2 LUFS', 'at most -0.1 dBTP' or 'at least -6 dBFS'."""
    u = f" {unit}" if unit else ""
    if lo is None:
        return f"at most {hi:g}{u}"
    if hi is None:
        return f"at least {lo:g}{u}"
    return f"{lo:g} to {hi:g}{u}"
