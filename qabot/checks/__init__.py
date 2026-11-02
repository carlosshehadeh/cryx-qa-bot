"""The registry: every check, in the order the report shows them.

Adding a check: a new file here with ID and run(ctx), one line in CHECKS,
and a test with a fixture that should PASS and one that should FAIL.
"""

import traceback

from qabot.report import FAIL, Result
from qabot.checks import (
    files_format, files_naming, stems_count, stems_silent, stems_length, stems_forbidden,
    stems_clipping, mix_headroom, null_test, master_loudness, master_peak, master_length,
    mixes_present, midi_present, privacy_metadata, privacy_names, private_files,
)

CHECKS = [
    files_format,
    files_naming,
    stems_count,
    stems_silent,
    stems_length,
    stems_forbidden,
    stems_clipping,
    mix_headroom,
    null_test,
    master_loudness,
    master_peak,
    master_length,
    mixes_present,
    midi_present,
    privacy_metadata,
    privacy_names,
    private_files,
]


def run_all(ctx, progress=None):
    results = []
    for i, check in enumerate(CHECKS):
        if progress:
            progress(i, len(CHECKS), check.ID)
        try:
            results += check.run(ctx)
        except Exception as e:  # one broken check must not stop the others
            results.append(Result(check.ID, FAIL, f"check crashed: {e}",
                                  "Copy this report to Claude so the check can be fixed.",
                                  numbers={"error": traceback.format_exc(limit=3)}))
    if progress:
        progress(len(CHECKS), len(CHECKS), "done")
    return results
