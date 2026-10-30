"""One run: scan the folder, load the rules, run every check, make the report."""

from dataclasses import dataclass

from qabot import __version__, rules as rules_mod
from qabot.checks import run_all
from qabot.context import Context
from qabot.report import Report, add_to_history
from qabot.scan import scan


@dataclass
class Run:
    report: Report
    export: object
    rules: dict
    context: Context


def check(folder, config, profile=None, bpm=None, title=None, key="", include_project=None,
          progress=None, history=True):
    profile = profile or config.default_profile
    rules = rules_mod.load(profile, config.rules_dir())
    export = scan(folder, config, title=title)
    if include_project is None:
        include_project = config.include_project
    ctx = Context(export, rules, config, bpm=bpm, include_project=include_project)
    report = Report(title=export.title, profile=rules.get("display", profile), folder=str(export.root),
                    version=__version__, bpm=ctx.bpm, key=key or "", site_notes=list(rules.get("notes", [])))
    report.results = run_all(ctx, progress)
    report.numbers = ctx.numbers
    if history:
        add_to_history(config.history_path(), report)
    return Run(report, export, rules, ctx)
