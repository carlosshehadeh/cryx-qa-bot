"""Portable settings: everything lives in one data folder next to the app.

When frozen as an .exe the data folder is "CryxQAData" beside the .exe; when
run from source it is "CryxQAData" in the repo folder. Nothing is ever written
to AppData, so copying the .exe and its data folder to another PC carries the
settings, rules and run history along.
"""

import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

DATA_FOLDER_NAME = "CryxQAData"
CONFIG_NAME = "config.json"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """Where files shipped with the app live (rules/, assets/)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def data_dir() -> Path:
    override = os.environ.get("CRYX_QA_DATA")
    d = Path(override) if override else app_dir() / DATA_FOLDER_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class Config:
    # Personal info that must never reach a buyer: real name, old and new
    # artist names, email, Windows user path ("C:\Users\Carlos").
    banned_words: list = field(default_factory=list)
    default_profile: str = "edmgp-tech-house"
    output_folder: str = ""        # empty: next to the export folder
    mp3: bool = True
    include_project: bool = False
    rules_folder: str = "rules"    # relative to the data folder

    # How the export folder is laid out (BRIEF.md section 4).
    export_suffix: str = " EXPORT"
    masters_folder: str = "Masters"
    stems_folders: dict = field(default_factory=lambda: {
        "Extended": "Stems Extended", "Radio": "Stems Radio"})
    project_folder: str = "Project"
    main_pattern: str = r"(^|[\s_-])Main$"   # file name (no extension) of the unmastered mix
    extended_pattern: str = "(Extended Mix)"
    radio_pattern: str = "(Radio Mix)"

    # Files that look private: never copied to the buyer folder.
    private_words: list = field(default_factory=lambda: [
        "license", "licence", "splice", "splice-log", "qa", "brief"])
    private_extensions: list = field(default_factory=lambda: [".pdf", ".txt", ".md"])

    # -- persistence ---------------------------------------------------
    @classmethod
    def load(cls, path=None):
        path = Path(path or data_dir() / CONFIG_NAME)
        cfg = cls()
        if not path.exists():
            cfg.save(path)
            return cfg
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return cfg
        for k, v in raw.items():
            if k in cls.__dataclass_fields__:
                setattr(cfg, k, v)
        return cfg

    def save(self, path=None):
        path = Path(path or data_dir() / CONFIG_NAME)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    # -- helpers -------------------------------------------------------
    def rules_dir(self) -> Path:
        """The editable rules folder. On first use the bundled rules are copied
        in; files Carlos already edited are never overwritten."""
        p = Path(self.rules_folder)
        d = p if p.is_absolute() else data_dir() / p
        d.mkdir(parents=True, exist_ok=True)
        for f in (bundle_dir() / "rules").glob("*.json"):
            if not (d / f.name).exists():
                shutil.copy2(f, d / f.name)
        return d

    def history_path(self) -> Path:
        return data_dir() / "history.json"
