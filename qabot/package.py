"""The buyer folder and zip.

`plan` decides what goes to the buyer and what stays behind (and why). The
privacy checks use the same plan, so the report and the zip always agree.
`build` writes the BUYER folder (clean WAV copies, MP3s, optional project)
and the zip, only when there are no FAILs, and checks the result again
before handing it over. Originals are only ever read.
"""

import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from qabot import clean, mp3
from qabot.audio import AUDIO_EXTENSIONS
from qabot.report import FAIL, WARN

SYSTEM_FILES = {"thumbs.db", "desktop.ini", ".ds_store"}
STORED = {".wav", ".wave", ".mp3", ".flac", ".aif", ".aiff", ".zip"}


class Refused(Exception):
    """The zip was not built; the message says why in plain English."""


@dataclass
class Item:
    src: Path
    dst: str        # path inside the BUYER folder, with forward slashes
    kind: str       # "wav" (clean copy), "mp3" (made from src), "copy"


@dataclass
class Plan:
    title: str
    items: list = field(default_factory=list)
    excluded: list = field(default_factory=list)   # (Path, reason)

    @property
    def folder_name(self):
        return f"{self.title} BUYER"

    def ships(self, path):
        return any(i.src == path for i in self.items)


def is_private(path, config):
    """Looks like a licence, Splice log, QA note, brief or other notes."""
    path = Path(path)
    if path.suffix.lower() in {e.lower() for e in config.private_extensions}:
        return True
    name = path.name.lower()
    tokens = set(re.split(r"[^a-z0-9]+", path.stem.lower()))
    for w in (w.lower() for w in config.private_words):
        if re.search(r"[^a-z0-9]", w) or len(w) >= 5:
            if w in name:
                return True
        elif w in tokens:
            return True
    return False


def plan(export, config, include_project=False, make_mp3=True):
    p = Plan(export.title)
    shipped = set()

    def add(src, dst, kind):
        p.items.append(Item(src, dst, kind))
        shipped.add(src)

    for kind in ("Extended", "Radio"):
        src = export.masters.get(kind)
        if src:
            add(src, src.name, "wav")
            if make_mp3:
                add(src, src.with_suffix(".mp3").name, "mp3")
    for src in export.unknown_masters:
        if src.suffix.lower() in (".wav", ".wave"):
            add(src, src.name, "wav")
    for s in export.stem_sets:
        for src in s.stems:
            if is_private(src, config):
                continue
            if src.suffix.lower() in (".wav", ".wave"):
                add(src, f"{s.label}/{src.name}", "wav")
        if s.main:
            p.excluded.append((s.main, "unmastered mix, only used for the null test"))
            shipped.add(s.main)
    if include_project and export.project:
        for src in sorted(export.project.rglob("*")):
            if not src.is_file():
                continue
            parts = {x.lower() for x in src.relative_to(export.project).parts[:-1]}
            if "backup" in parts:
                p.excluded.append((src, "Ableton backup copy"))
            elif src.suffix.lower() == ".asd":
                p.excluded.append((src, "Ableton analysis file (Live remakes it)"))
            elif src.name.lower() in SYSTEM_FILES or src.name.startswith("."):
                p.excluded.append((src, "system file"))
            elif is_private(src, config):
                p.excluded.append((src, "looks private"))
            else:
                add(src, f"{config.project_folder}/{src.relative_to(export.project).as_posix()}", "copy")
            shipped.add(src)
    for src in export.files:
        if src in shipped:
            continue
        if is_private(src, config):
            p.excluded.append((src, "looks private"))
        elif export.project and export.project in src.parents:
            p.excluded.append((src, "project not included"))
        elif src.suffix.lower() in AUDIO_EXTENSIONS and src.suffix.lower() not in (".wav", ".wave"):
            p.excluded.append((src, "not a WAV"))
        else:
            p.excluded.append((src, "not part of the delivery"))
    return p


def output_root(export, config):
    return Path(config.output_folder) if config.output_folder else export.root.parent


@dataclass
class Built:
    folder: Path
    zip: Path
    report: Path
    files: int


def build(export, config, report, include_project=False, make_mp3=True, warnings_ok=False,
          bitrate=320, progress=None):
    if report.count(FAIL):
        raise Refused(f"Not built: {report.count(FAIL)} check(s) failed. Fix them and run the checks again.")
    if report.count(WARN) and not warnings_ok:
        raise Refused("Not built: confirm the warnings first ('I checked these').")

    pl = plan(export, config, include_project, make_mp3)
    out = output_root(export, config)
    out.mkdir(parents=True, exist_ok=True)
    buyer = out / pl.folder_name
    root = export.root.resolve()
    if buyer.resolve() == root or root in buyer.resolve().parents or buyer.resolve() in root.parents:
        raise Refused("Not built: the output folder can't be inside the export folder. Change it in Settings.")
    if buyer.exists():
        shutil.rmtree(buyer)     # our own output from an earlier run
    buyer.mkdir()

    for i, item in enumerate(pl.items):
        if progress:
            progress(i, len(pl.items), item.dst)
        dst = buyer / item.dst
        dst.parent.mkdir(parents=True, exist_ok=True)
        if item.kind == "wav":
            clean.clean_copy(item.src, dst)
        elif item.kind == "mp3":
            mp3.encode(item.src, dst, bitrate)
        else:
            shutil.copy2(item.src, dst)

    problems = verify_folder(buyer, export, config)
    if problems:
        shutil.rmtree(buyer)
        raise Refused("Not built: " + " ".join(problems))

    zip_path = out / f"{pl.folder_name}.zip"
    tmp = zip_path.with_name(zip_path.name + ".part")
    with zipfile.ZipFile(tmp, "w") as z:
        for f in sorted(buyer.rglob("*")):
            if f.is_file():
                how = zipfile.ZIP_STORED if f.suffix.lower() in STORED else zipfile.ZIP_DEFLATED
                z.write(f, f"{pl.folder_name}/{f.relative_to(buyer).as_posix()}", compress_type=how)
    problems = verify_zip(tmp, export, config)
    if problems:
        tmp.unlink()
        raise Refused("Zip refused: " + " ".join(problems))
    tmp.replace(zip_path)
    report_path = report.write(out / f"{pl.title} QA REPORT.md")
    if progress:
        progress(len(pl.items), len(pl.items), "done")
    return Built(buyer, zip_path, report_path, len(pl.items))


def _private_name(name, export, config):
    """Why a path inside the buyer folder or zip must not be there, or ''."""
    from qabot.scan import is_main
    p = Path(name)
    if p.suffix.lower() in (".wav", ".wave") and is_main(p, config.main_pattern):
        return f"'{name}' is the unmastered Main mix."
    if is_private(p, config):
        return f"'{name}' looks private."
    low = name.lower().replace("\\", "/")
    for w in config.banned_words:
        w = w.strip().lower()
        if w and (w in low or w.replace("\\", "/") in low):
            return f"'{name}' contains a banned word."
    return ""


def verify_folder(buyer, export, config):
    problems = []
    for f in sorted(buyer.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(buyer).as_posix()
        why = _private_name(rel, export, config)
        if why:
            problems.append(why)
        if f.suffix.lower() in (".wav", ".wave"):
            extra = [c for c in clean.chunk_ids(f) if c not in clean.KEEP]
            if extra:
                problems.append(f"'{rel}' still has hidden chunks ({', '.join(extra)}).")
    return problems


def verify_zip(path, export, config):
    with zipfile.ZipFile(path) as z:
        return [why for why in (_private_name(n, export, config) for n in z.namelist()) if why]
