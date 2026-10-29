"""The masters (and stem folders) the profile needs are all there."""

from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import MIX_LABEL, rel

ID = "mixes_present"


def run(ctx):
    need = ctx.rules["mixes"]
    ex = ctx.export
    out = []
    if not ex.masters_folder:
        out.append(Result(ID, FAIL, f"No '{ctx.config.masters_folder}' folder in the export.",
                          f"Put the mastered WAVs in a '{ctx.config.masters_folder}' folder."))
    for kind, key in (("Extended", "extended_required"), ("Radio", "radio_required")):
        if need.get(key) and kind not in ex.masters:
            pattern = ctx.config.extended_pattern if kind == "Extended" else ctx.config.radio_pattern
            out.append(Result(ID, FAIL, f"The {MIX_LABEL[kind]} master is missing.",
                              f"Export it with the master rack on and name it '{ex.title} {pattern}.wav'."))
    if ex.unknown_masters:
        out.append(Result(ID, WARN, "Can't tell which mix these masters are.",
                          f"Put '{ctx.config.extended_pattern}' or '{ctx.config.radio_pattern}' in the file name.",
                          files=[rel(ctx, p) for p in ex.unknown_masters]))
    if not ex.stem_set("Extended"):
        out.append(Result(ID, FAIL, f"No '{ctx.config.stems_folders.get('Extended')}' folder.",
                          "Export the extended mix stems into it."))
    if need.get("radio_stems_required") and not ex.stem_set("Radio"):
        out.append(Result(ID, FAIL, f"No '{ctx.config.stems_folders.get('Radio')}' folder, and this profile needs radio stems.",
                          "Export the radio mix stems into it."))
    if not out:
        have = [MIX_LABEL[k] for k in ("Extended", "Radio") if k in ex.masters]
        out.append(Result(ID, PASS, f"Masters present: {', '.join(have)}."))
    return out
