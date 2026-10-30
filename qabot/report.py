"""Results, the Markdown report and the run history.

Every check returns a list of Result objects. The Report collects them with
the numbers worth keeping (LUFS, peaks, residual, lengths) and writes the
Markdown that Carlos pastes into the track's qa.md.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
LEVELS = (PASS, WARN, FAIL)
ICON = {PASS: "✅", WARN: "⚠️", FAIL: "❌"}

HISTORY_NAME = "history.json"


@dataclass
class Result:
    check_id: str      # "stems_silent"
    level: str         # "PASS", "WARN" or "FAIL"
    message: str       # plain English: "Stem 'Perc 2.wav' is silent"
    fix: str = ""      # plain English: "Delete it, or unmute the track and re-export"
    files: list = field(default_factory=list)
    numbers: dict = field(default_factory=dict)   # shown when the row is clicked


def worst(levels):
    levels = list(levels)
    if FAIL in levels:
        return FAIL
    if WARN in levels:
        return WARN
    return PASS


@dataclass
class Report:
    title: str
    profile: str
    folder: str
    version: str
    bpm: float = 0.0
    key: str = ""
    when: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    results: list = field(default_factory=list)
    numbers: dict = field(default_factory=dict)   # {"Masters": {...}, "Stems Extended": {...}}
    site_notes: list = field(default_factory=list)  # site rules the bot can't check, to remember

    # -- summary --------------------------------------------------------
    def count(self, level):
        return sum(1 for r in self.results if r.level == level)

    @property
    def overall(self):
        return worst(r.level for r in self.results)

    def exit_code(self):
        """0 = all pass, 1 = warnings only, 2 = at least one fail (for Conductor)."""
        return {PASS: 0, WARN: 1, FAIL: 2}[self.overall]

    def summary(self):
        return (f"{self.overall}: {self.count(FAIL)} fail, {self.count(WARN)} warn, "
                f"{self.count(PASS)} pass")

    # -- markdown -------------------------------------------------------
    def to_markdown(self):
        out = [f"# QA REPORT: {self.title}", ""]
        out.append(f"- Date: {self.when}")
        out.append(f"- Profile: {self.profile}")
        if self.bpm:
            out.append(f"- BPM: {self.bpm:g}")
        if self.key:
            out.append(f"- Key: {self.key}")
        out.append(f"- Export folder: `{self.folder}`")
        out.append(f"- Cryx QA Bot {self.version}")
        out.append("")
        out.append(f"**{ICON[self.overall]} {self.summary()}**")
        out.append("")
        out.append("## Checks")
        out.append("")
        out.append("| | Check | Result | Fix |")
        out.append("|---|---|---|---|")
        for r in sorted(self.results, key=lambda r: -LEVELS.index(r.level)):
            out.append(f"| {ICON[r.level]} | `{r.check_id}` | {_cell(r.message)} | {_cell(r.fix)} |")
        details = [r for r in self.results if r.level != PASS and r.files]
        if details:
            out.append("")
            out.append("## Files behind the warnings and fails")
            for r in details:
                out.append("")
                out.append(f"**{r.check_id}**: {r.message}")
                out.extend(f"- {f}" for f in r.files)
        if self.numbers:
            out.append("")
            out.append("## Numbers")
            for section, values in self.numbers.items():
                out.append("")
                out.append(f"**{section}**")
                out.append("")
                out.extend(f"- {k}: {v}" for k, v in values.items())
        if self.site_notes:
            out.append("")
            out.append("## Site rules to remember (not checked by the bot)")
            out.append("")
            out.extend(f"- {n}" for n in self.site_notes)
        out.append("")
        out.append("## For qa.md")
        out.append("")
        out.append("```")
        out.append(self.qa_block())
        out.append("```")
        out.append("")
        return "\n".join(out)

    def qa_block(self):
        """Short block to paste into the track's qa.md."""
        lines = [f"QA Bot {self.version}, {self.when}, profile {self.profile}: {self.summary()}"]
        for r in self.results:
            box = "x" if r.level == PASS else " "
            lines.append(f"- [{box}] {r.level} {r.check_id}: {r.message}")
        return "\n".join(lines)

    def write(self, path):
        path = Path(path)
        path.write_text(self.to_markdown(), encoding="utf-8")
        return path

    def history_entry(self):
        return {"date": self.when, "title": self.title, "profile": self.profile,
                "folder": self.folder, "version": self.version, "overall": self.overall,
                "fail": self.count(FAIL), "warn": self.count(WARN), "pass": self.count(PASS),
                "fails": [r.check_id for r in self.results if r.level == FAIL]}

    def to_dict(self):
        return asdict(self)


def _cell(text):
    return (text or "").replace("|", "/").replace("\n", " ")


# -- history ---------------------------------------------------------------
def load_history(path):
    path = Path(path)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def add_to_history(path, report):
    path = Path(path)
    runs = load_history(path)
    runs.append(report.history_entry())
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(runs, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return runs


def runs_for(runs, title):
    return [r for r in runs if r.get("title", "").lower() == (title or "").lower()]
