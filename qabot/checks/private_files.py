"""Private-looking files (licences, Splice logs, QA notes, briefs, PDFs, .txt,
.md) are never copied to the buyer folder; this lists them so nothing is a
surprise."""

from qabot import package
from qabot.report import PASS, WARN, Result
from qabot.checks._util import plural, rel

ID = "private_files"


def run(ctx):
    found = [p for p in ctx.export.files if package.is_private(p, ctx.config)]
    if not found:
        return [Result(ID, PASS, "No private-looking files in the export folder.")]
    return [Result(ID, WARN, f"{plural(len(found), 'private-looking file')} in the export folder. "
                             "They will not be copied to the buyer zip.",
                   "Fine to leave them. Check the list in case something the buyer needs was caught.",
                   files=[rel(ctx, p) for p in found])]
