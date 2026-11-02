"""The masters, unmastered mixes and stem folders the site needs are all there."""

from qabot.report import FAIL, PASS, WARN, Result
from qabot.checks._util import MIX_LABEL, rel

ID = "mixes_present"


def run(ctx):
    need = ctx.rules["mixes"]
    ex, cfg = ctx.export, ctx.config
    out = []
    if not ex.masters_folder:
        out.append(Result(ID, FAIL, f"No '{cfg.masters_folder}' folder in the export.",
                          f"Put the mastered WAVs in a '{cfg.masters_folder}' folder."))
    if need.get("extended_required") and "Extended" not in ex.masters:
        out.append(Result(ID, FAIL, "The Extended Mix master is missing.",
                          f"Export it with the master rack on and name it '{ex.title} {cfg.extended_pattern}.wav'."))
    if "Radio" not in ex.masters:
        level = FAIL if need.get("radio_required") else need.get("radio_level", PASS)
        if level != PASS:
            out.append(Result(ID, level, "The Radio Mix master is missing"
                              + (" (this site needs one for this genre)." if level == FAIL else " (recommended)."),
                              f"Export it with the master rack on and name it '{ex.title} {cfg.radio_pattern}.wav'."))
    if ex.unknown_masters:
        out.append(Result(ID, WARN, "Can't tell which mix these masters are.",
                          f"Put '{cfg.extended_pattern}' or '{cfg.radio_pattern}' in the file name.",
                          files=[rel(ctx, p) for p in ex.unknown_masters]))
    if not ex.stem_set("Extended"):
        out.append(Result(ID, FAIL, f"No '{cfg.stems_folders.get('Extended')}' folder.",
                          "Export the extended mix stems into it."))
    if need.get("radio_stems_required") and not ex.stem_set("Radio"):
        out.append(Result(ID, FAIL, f"No '{cfg.stems_folders.get('Radio')}' folder, and this site needs radio stems.",
                          "Export the radio mix stems into it."))
    if need.get("unmastered_required"):
        wanted = [k for k in ex.masters if need.get("unmastered_each_version") or k == "Extended"]
        for kind in wanted or ["Extended"]:
            if kind not in ex.unmastered:
                where = (f"'Main.wav' in '{cfg.stems_folders.get(kind)}'" if kind == "Extended" else
                         f"'{ex.title} {cfg.radio_pattern}.wav' in an '{cfg.unmastered_folder}' folder")
                out.append(Result(ID, FAIL, f"The unmastered {MIX_LABEL[kind]} (master chain off) is missing; "
                                            "this site wants it in the package.",
                                  f"Export the Main track with the master rack off and save it as {where}."))
    if not out:
        have = [MIX_LABEL[k] for k in ("Extended", "Radio") if k in ex.masters]
        um = [MIX_LABEL[k] for k in ("Extended", "Radio") if k in ex.unmastered]
        out.append(Result(ID, PASS, f"Masters: {', '.join(have) or 'none'}. Unmastered: {', '.join(um) or 'none'}."))
    return out
