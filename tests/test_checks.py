"""Every check: a fixture that should PASS and one that should FAIL (or WARN)."""

import gzip

import pytest

from qabot.checks import (
    CHECKS, files_format, files_naming, master_length, master_loudness, master_peak, mix_headroom,
    mixes_present, privacy_metadata, privacy_names, private_files, stems_clipping, stems_count,
    stems_forbidden, stems_length, stems_silent,
)
from qabot.checks import run_all
from qabot.report import FAIL, PASS, WARN
from tests.conftest import levels


def test_registry_has_every_check_once():
    ids = [c.ID for c in CHECKS]
    assert len(ids) == len(set(ids)) == 17


def test_a_crashing_check_fails_alone(export, ctx_for, monkeypatch):
    ctx = ctx_for(export())
    monkeypatch.setattr(stems_count, "run", lambda ctx: 1 / 0)
    results = run_all(ctx)
    crashed = [r for r in results if r.check_id == "stems_count"]
    assert crashed[0].level == FAIL and "check crashed" in crashed[0].message
    assert any(r.check_id == "null_test" for r in results)


def test_files_format(export, ctx_for):
    assert levels(files_format.run(ctx_for(export()))) == [PASS]
    bad = files_format.run(ctx_for(export("Wrong Format", stem_48k=True, stem_24bit=True)))
    assert levels(bad) == [FAIL, FAIL]
    text = " ".join(f for r in bad for f in r.files)
    assert "10 FX Sweep.wav: 48 kHz" in text and "07 Tone A.wav: 24-bit, needs 16-bit" in text
    # House of Tracks wants 24 or 32-bit and takes 48 kHz.
    hot = files_format.run(ctx_for(export("Hot Format", bits=24), profile="hot-tech-house"))
    assert levels(hot) == [PASS]
    assert levels(files_format.run(ctx_for(export(), profile="hot-tech-house"))) == [FAIL]


def test_files_naming(export, ctx_for):
    assert levels(files_naming.run(ctx_for(export()))) == [PASS]
    r = files_naming.run(ctx_for(export("Default Names", default_names=True)))
    assert levels(r) == [WARN] and r[0].files == ["Stems Extended/13 Audio 12.wav"]


def test_stems_count(export, ctx_for):
    assert levels(stems_count.run(ctx_for(export()))) == [PASS]
    assert levels(stems_count.run(ctx_for(export("Few Stems", n_stems=8)))) == [FAIL]


def test_stems_silent(export, ctx_for):
    assert levels(stems_silent.run(ctx_for(export()))) == [PASS]
    r = stems_silent.run(ctx_for(export("Silent Stem", silent_stem=True)))
    assert levels(r) == [FAIL] and "09 Noise Bed" in r[0].message


def test_stems_length(export, ctx_for):
    assert levels(stems_length.run(ctx_for(export()))) == [PASS]
    r = stems_length.run(ctx_for(export("Short Stem", short_stem=True)))
    assert levels(r) == [FAIL] and r[0].files == ["Stems Extended/08 Tone B.wav: -1000 samples (0:30)"]


def test_stems_forbidden(export, ctx_for):
    assert levels(stems_forbidden.run(ctx_for(export()))) == [PASS]
    r = stems_forbidden.run(ctx_for(export("Ref Stem", ref_stem=True)))
    assert levels(r) == [FAIL] and "REF Track.wav" in r[0].files[0]


@pytest.mark.parametrize("name,hit", [
    ("SC TRIG", True), ("sc-trig kick", True), ("Bass BUS", True), ("Drum Group", True),
    ("Master", True), ("Busy Hats", False), ("Reverb", False), ("Mastering Noise", False),
])
def test_forbidden_word_matching(name, hit):
    from qabot.checks._util import word_pattern
    words = ["REF", "SC TRIG", "Sidechain", "BUS", "GROUP", "Master"]
    assert any(word_pattern(w).search(name) for w in words) == hit


def test_stems_clipping(export, ctx_for):
    assert levels(stems_clipping.run(ctx_for(export()))) == [PASS]
    r = stems_clipping.run(ctx_for(export("Clipped", clip_stem=True)))
    assert levels(r) == [FAIL] and "04 Perc.wav" in r[0].files[0] and "run 5" in r[0].files[0]


def test_mix_headroom(export, ctx_for):
    # Extended (Main.wav) and radio (Unmastered folder) unmastered mixes.
    assert levels(mix_headroom.run(ctx_for(export()))) == [PASS, PASS]
    assert levels(mix_headroom.run(ctx_for(export("Hot Mix", main_peak_db=-1.0)))) == [FAIL, FAIL]
    assert levels(mix_headroom.run(ctx_for(export("Quiet Mix", main_peak_db=-9.0)))) == [WARN, WARN]
    # The Ghost Production only asks for at least 3 dB of headroom.
    assert levels(mix_headroom.run(ctx_for(export("Quiet Mix", main_peak_db=-9.0), profile="tgp-tech-house"))) == \
        [PASS, PASS]
    assert levels(mix_headroom.run(ctx_for(export("No Main", main=False, radio_unmastered=False)))) == [WARN]


def test_master_loudness(export, ctx_for):
    r = master_loudness.run(ctx_for(export()))
    assert levels(r) == [PASS, PASS]
    assert -8.6 < r[0].numbers["integrated_lufs"] < -7.4
    assert levels(master_loudness.run(ctx_for(export("Quiet Master", master_lufs=-12.0)))) == [FAIL, FAIL]


def test_master_peak(export, ctx_for):
    folder = export()
    wide = {"peak_min_db": -3.0, "peak_max_db": 0.0, "peak_confirmed": True}
    assert levels(master_peak.run(ctx_for(folder, master=wide))) == [PASS, PASS]
    tight = {"peak_min_db": -0.1, "peak_max_db": 0.0, "peak_confirmed": True}
    assert levels(master_peak.run(ctx_for(folder, master=tight))) == [FAIL, FAIL]
    tight["peak_confirmed"] = False   # open question: only a warning until confirmed
    assert levels(master_peak.run(ctx_for(folder, master=tight))) == [WARN, WARN]


def test_master_length(export, ctx_for):
    good = export("Plan Length", extended_seconds=390, radio_seconds=180)
    assert levels(master_length.run(ctx_for(good))) == [PASS, PASS]
    r = master_length.run(ctx_for(export("Odd Lengths", extended_seconds=200, radio_seconds=100)))
    assert levels(r) == [WARN, FAIL]


def test_mixes_present(export, ctx_for):
    assert levels(mixes_present.run(ctx_for(export()))) == [PASS]
    r = mixes_present.run(ctx_for(export("No Radio", radio_seconds=0)))
    assert levels(r) == [FAIL] and "Radio Mix" in r[0].message
    assert FAIL in levels(mixes_present.run(ctx_for(export("No Masters", masters=False))))
    need_stems = mixes_present.run(ctx_for(export(), mixes={"radio_stems_required": True}))
    assert levels(need_stems) == [FAIL]


def test_privacy_metadata(export, ctx_for):
    r = privacy_metadata.run(ctx_for(export()))
    assert levels(r) == [PASS] and "No hidden chunks" in r[0].message
    r = privacy_metadata.run(ctx_for(export("Hidden Tags", metadata=True, credential=True)))
    assert levels(r) == [WARN, PASS]
    assert "C2PA" in r[0].message and "02 Clap.wav" in r[0].files[0]
    assert "LIST" in r[1].message and "bext" in r[1].message


def test_privacy_names(export, ctx_for, config):
    folder = export()
    assert levels(privacy_names.run(ctx_for(folder))) == [PASS]
    config.banned_words = []
    assert levels(privacy_names.run(ctx_for(folder))) == [WARN]
    config.banned_words = ["Carlos Test", "C:\\Users\\Carlos"]

    named = export("Carlos Test Song")   # the title becomes the zip name
    r = privacy_names.run(ctx_for(named))
    assert FAIL in levels(r)

    als = export("With Project", als_text='<Path Value="C:/Users/Carlos/Music/kick.wav" />')
    assert levels(privacy_names.run(ctx_for(als))) == [WARN]                  # project not shipped
    r = privacy_names.run(ctx_for(als, include_project=True))
    assert levels(r) == [FAIL] and "inside the file" in r[0].files[0]


def test_private_files(export, ctx_for):
    assert levels(private_files.run(ctx_for(export()))) == [PASS]
    r = private_files.run(ctx_for(export("Private Files", private_file=True)))
    assert levels(r) == [WARN]
    assert sorted(r[0].files) == ["Masters/qa notes.md", "Splice License.pdf"]


def test_midi_present(export, ctx_for):
    from qabot.checks import midi_present
    assert levels(midi_present.run(ctx_for(export()))) == [PASS]
    assert levels(midi_present.run(ctx_for(export("No Midi", midi=False)))) == [FAIL]


def test_unmastered_each_version(export, ctx_for):
    """EDM GP wants an unmastered mix for every version; TGP only the main one."""
    folder = export("No Radio Unmastered", radio_unmastered=False)
    r = mixes_present.run(ctx_for(folder))
    assert levels(r) == [FAIL] and "unmastered Radio Mix" in r[0].message
    assert levels(mixes_present.run(ctx_for(folder, profile="tgp-tech-house"))) == [PASS]


def test_site_rules_differ(export, ctx_for):
    folder = export()
    # TGP: no LUFS target, extended mix 4 to 8 minutes is only a recommendation.
    assert "no LUFS target" in master_loudness.run(ctx_for(folder, profile="tgp-tech-house"))[0].message
    assert levels(master_length.run(ctx_for(folder, profile="tgp-tech-house"))) == [WARN, PASS]
    # HoT: 2:30 minimum, so a 2:10 extended mix fails.
    assert levels(master_length.run(ctx_for(folder, profile="hot-tech-house")))[0] == FAIL
    # HoT asks for bus stems, EDM GP forbids grouped stems.
    assert "BUS" not in ctx_for(folder, profile="hot-tech-house").rules["stems"]["forbidden_names"]
    assert "BUS" in ctx_for(folder).rules["stems"]["forbidden_names"]


def test_is_private_words():
    from qabot.config import Config
    from qabot.package import is_private
    cfg = Config()
    for name in ("Splice License.pdf", "splice-log.csv", "Track QA.xlsx", "brief.docx", "notes.txt"):
        assert is_private(name, cfg), name
    for name in ("Aqua Lead.wav", "01 Kick.wav", "Main.wav"):
        assert not is_private(name, cfg), name
