"""Command line for the same engine (for Cryx Conductor and quick runs).

    cryx-qa check "<folder>" --profile edmgp-tech-house
    cryx-qa check "<folder>" --build --ok-warnings
    cryx-qa profiles

Exit code: 0 = all pass, 1 = warnings only, 2 = at least one fail
(3 = the folder or profile couldn't be used).
"""

import argparse
import sys

from qabot import __version__, package, rules
from qabot.config import Config


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cryx-qa", description=f"Cryx QA Bot {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check an export folder")
    c.add_argument("folder")
    c.add_argument("--profile", help="rules profile, e.g. edmgp-tech-house (default from Settings)")
    c.add_argument("--bpm", type=float, help="track BPM for the bar numbers (default from the profile)")
    c.add_argument("--title", help="track title (default: folder name without ' EXPORT')")
    c.add_argument("--key", default="", help="track key, shown in the report")
    c.add_argument("--report", help="also save the Markdown report to this file")
    c.add_argument("--build", action="store_true", help="build the BUYER folder and zip if nothing failed")
    c.add_argument("--ok-warnings", action="store_true", help="with --build: I checked the warnings")
    c.add_argument("--include-project", action="store_true", help="with --build: add the Project folder")
    c.add_argument("--no-mp3", action="store_true", help="with --build: skip the MP3s")
    c.add_argument("--quiet", action="store_true", help="print only the summary line")
    sub.add_parser("profiles", help="list the rules profiles")
    args = ap.parse_args(argv)
    config = Config.load()

    if args.cmd == "profiles":
        for pid, name in rules.profiles(config.rules_dir()).items():
            print(f"{pid:32} {name}")
        return 0

    from qabot.engine import check
    try:
        run = check(args.folder, config, profile=args.profile, bpm=args.bpm, title=args.title,
                    key=args.key, include_project=args.include_project or config.include_project)
    except (FileNotFoundError, ValueError) as e:
        print(f"Can't check: {e}", file=sys.stderr)
        return 3
    report = run.report
    print(report.summary() if args.quiet else report.to_markdown())
    if args.report:
        report.write(args.report)
    if args.build:
        try:
            built = package.build(run.export, config, report,
                                  include_project=args.include_project or config.include_project,
                                  make_mp3=config.mp3 and not args.no_mp3, warnings_ok=args.ok_warnings,
                                  bitrate=run.rules.get("mp3", {}).get("bitrate_kbps", 320))
            print(f"Built {built.zip} ({built.files} files). Report: {built.report}")
        except package.Refused as e:
            print(str(e), file=sys.stderr)
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
