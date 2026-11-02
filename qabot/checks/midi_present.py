"""The MIDI of the melodic parts is there, when the site asks for it.

The bot only looks for the files and copies them as they are. It never
writes, changes or judges notes.
"""

from qabot.report import FAIL, PASS, Result
from qabot.checks._util import plural

ID = "midi_present"


def run(ctx):
    if not ctx.rules.get("midi", {}).get("required"):
        return [Result(ID, PASS, f"This site doesn't ask for MIDI ({plural(len(ctx.export.midi), 'file')} found).")]
    if not ctx.export.midi:
        return [Result(ID, FAIL, f"No MIDI files in a '{ctx.config.midi_folder}' folder; this site wants the "
                                 "MIDI of every melodic part.",
                       f"Export each melodic clip (bass, lead, chords, arp...) as its own .mid file into a "
                       f"'{ctx.config.midi_folder}' folder in the export, named like the stem.")]
    return [Result(ID, PASS, f"{plural(len(ctx.export.midi), 'MIDI file')} found.",
                   files=[p.name for p in ctx.export.midi])]
