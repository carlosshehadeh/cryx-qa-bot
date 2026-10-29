"""Banned words (real name, artist names, email, Windows user path) must not
appear in anything that reaches the buyer: file and folder names, the zip
name, or inside an Ableton project file."""

import gzip

from qabot import package
from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import rel

ID = "privacy_names"
ABLETON_FILES = {".als", ".alc", ".adg", ".adv"}


def _variants(word):
    w = word.strip().lower()
    return {w, w.replace("\\", "/"), w.replace("/", "\\")} - {""}


def _hit(text, banned):
    low = text.lower()
    return next((w for w, vs in banned if any(v in low for v in vs)), None)


def _inside(path, banned):
    """Banned word inside an Ableton file (gzipped XML), or None."""
    try:
        with gzip.open(path, "rb") as f:
            raw = f.read()
    except OSError:
        raw = path.read_bytes()
    return _hit(raw.decode("utf-8", "ignore"), banned)


def run(ctx):
    words = [w for w in ctx.config.banned_words if w.strip()]
    if not words:
        return [Result(ID, WARN, "The banned words list is empty, so personal info can't be checked.",
                       "Open Settings and add your real name, old and new artist names, email and "
                       "Windows user folder (C:\\Users\\...).")]
    banned = [(w, _variants(w)) for w in words]
    pl = package.plan(ctx.export, ctx.config, getattr(ctx, "include_project", False))
    fails, warns = [], []

    w = _hit(pl.folder_name, banned)
    if w:
        fails.append(f"zip and folder name '{pl.folder_name}': '{w}'")
    for p in ctx.export.files:
        target = fails if pl.ships(p) else warns
        w = _hit(rel(ctx, p), banned)
        if w:
            target.append(f"{rel(ctx, p)}: name contains '{w}'")
        if p.suffix.lower() in ABLETON_FILES:
            w = _inside(p, banned)
            if w:
                target.append(f"{rel(ctx, p)}: '{w}' inside the file")

    out = []
    if fails:
        out.append(Result(ID, FAIL, f"Personal info in {len(fails)} place(s) that would reach the buyer.",
                          "Rename the file or folder. For a project file, use File > Collect All and Save so "
                          "sample paths point inside the project, and check the track and clip names.",
                          files=fails))
    if warns:
        out.append(Result(ID, WARN, f"Personal info in {len(warns)} file(s) that stay with you (not in the zip).",
                          "Nothing to do for the buyer. Rename them if you share the export folder.", files=warns))
    return out or [Result(ID, PASS, f"No banned words found ({len(words)} checked).")]
