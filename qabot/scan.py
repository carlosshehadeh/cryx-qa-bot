"""Find masters, stems, the Main file and everything else in an export folder.

Expected layout (BRIEF.md section 4), all names from config.json:

    <Title> EXPORT\\
      Masters\\        <Title> (Extended Mix).wav, <Title> (Radio Mix).wav
      Stems Extended\\ 01 Kick.wav ... Main.wav (unmastered mix, null test only)
      Stems Radio\\    same, if radio stems are delivered
      Project\\        optional: .als + samples
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from qabot.audio import AUDIO_EXTENSIONS


@dataclass
class StemSet:
    name: str                  # "Extended" or "Radio"
    folder: Path
    stems: list = field(default_factory=list)    # audio files, Main excluded
    main: Path = None
    other: list = field(default_factory=list)    # non-audio files in the folder

    @property
    def label(self):
        return f"Stems {self.name}"


@dataclass
class ExportFolder:
    root: Path
    title: str
    masters_folder: Path = None
    masters: dict = field(default_factory=dict)  # "Extended"/"Radio" -> Path
    unknown_masters: list = field(default_factory=list)
    stem_sets: list = field(default_factory=list)
    project: Path = None
    files: list = field(default_factory=list)    # every file, for the privacy checks
    problems: list = field(default_factory=list)  # plain-English layout problems

    def all_wavs(self):
        wavs = list(self.masters.values()) + list(self.unknown_masters)
        for s in self.stem_sets:
            wavs += s.stems + ([s.main] if s.main else [])
        return [p for p in wavs if p.suffix.lower() in (".wav", ".wave")]

    def stem_set(self, name):
        return next((s for s in self.stem_sets if s.name == name), None)


def title_from_folder(name, suffix):
    if suffix and name.lower().endswith(suffix.lower()):
        name = name[: -len(suffix)]
    return name.strip()


def _find_dir(root, name):
    """Folder by name, ignoring upper/lower case."""
    exact = root / name
    if exact.is_dir():
        return exact
    for d in root.iterdir():
        if d.is_dir() and d.name.lower() == name.lower():
            return d
    return None


def is_main(path, pattern):
    return re.search(pattern, path.stem, re.IGNORECASE) is not None


def scan(root, config, title=None) -> ExportFolder:
    root = Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"Folder not found: {root}")
    ex = ExportFolder(root, title or title_from_folder(root.name, config.export_suffix))
    ex.files = sorted(p for p in root.rglob("*") if p.is_file())

    ex.masters_folder = _find_dir(root, config.masters_folder)
    if ex.masters_folder:
        for p in sorted(ex.masters_folder.iterdir()):
            if not p.is_file() or p.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            low = p.stem.lower()
            if config.extended_pattern.lower() in low and "Extended" not in ex.masters:
                ex.masters["Extended"] = p
            elif config.radio_pattern.lower() in low and "Radio" not in ex.masters:
                ex.masters["Radio"] = p
            else:
                ex.unknown_masters.append(p)
    else:
        ex.problems.append(f"No '{config.masters_folder}' folder in the export.")

    for name, folder_name in config.stems_folders.items():
        d = _find_dir(root, folder_name)
        if not d:
            continue
        s = StemSet(name, d)
        for p in sorted(d.iterdir()):
            if not p.is_file():
                continue
            if p.suffix.lower() not in AUDIO_EXTENSIONS:
                s.other.append(p)
            elif is_main(p, config.main_pattern) and s.main is None:
                s.main = p
            else:
                s.stems.append(p)
        ex.stem_sets.append(s)
    if not ex.stem_sets:
        wanted = " or ".join(f"'{n}'" for n in config.stems_folders.values())
        ex.problems.append(f"No stems folder ({wanted}) in the export.")

    ex.project = _find_dir(root, config.project_folder)
    return ex
