"""One rules profile per website and genre, and the rule shapes they need."""

import pytest

from qabot import engine, rules as rules_mod
from qabot.checks import files_format, master_length, master_loudness, master_peak, mix_headroom, mixes_present
from qabot.context import Context
from qabot.report import FAIL, PASS, WARN
from qabot.scan import scan
from tests.conftest import levels

SITES = {"EDM Ghost Production": "edmgp", "The Ghost Production": "tgp", "House of Tracks": "hot"}
GENRES = {"Tech House": "tech-house", "Melodic House & Techno": "melodic-house-techno"}


def ctx_with(folder, config, profile):
    return Context(scan(folder, config), rules_mod.load(profile), config)


def test_every_website_has_both_genres(config):
    cat = rules_mod.catalog(config.rules_dir())
    assert rules_mod.marketplaces(config.rules_dir()) == sorted(SITES, key=str.lower)
    for site, prefix in SITES.items():
        for genre, suffix in GENRES.items():
            p = cat[f"{prefix}-{suffix}"]
            assert p["marketplace"] == site and p["genre"] == genre
            r = rules_mod.load(f"{prefix}-{suffix}")
            assert r["checklist"] and r["_source"]


def test_list_of_formats(export, ctx_for):
    folder = export("Wrong Format", stem_48k=True, stem_24bit=True)
    assert levels(files_format.run(ctx_for(folder, format={"sample_rate": [44100, 48000]}))) == [FAIL]
    loose = {"sample_rate": [44100, 48000], "bit_depth": [16, 24]}
    assert levels(files_format.run(ctx_for(folder, format=loose))) == [PASS]


def test_house_of_tracks_wants_24_bit(export, config):
    r = files_format.run(ctx_with(export(), config, "hot-tech-house"))
    assert levels(r) == [FAIL] and "24 or 32-bit" in r[0].message
    assert "Bit Depth to 24" in r[0].fix


def test_open_ended_limits(export, config):
    ctx = ctx_with(export(), config, "tgp-tech-house")
    loud = master_loudness.run(ctx)
    assert levels(loud) == [PASS, PASS] and "no LUFS range" in loud[0].message
    assert levels(mix_headroom.run(ctx)) == [PASS]
    assert levels(mix_headroom.run(ctx_with(export("Quiet Mix", main_peak_db=-9.0), config, "tgp-tech-house"))) == [PASS]
    assert all("at most -0.1" in r.message for r in master_peak.run(ctx))


def test_house_of_tracks_loudness(export, config):
    assert levels(master_loudness.run(ctx_with(export(), config, "hot-tech-house"))) == [PASS, PASS]
    quiet = export("Quiet Master", master_lufs=-12.0)
    r = master_loudness.run(ctx_with(quiet, config, "hot-tech-house"))
    assert levels(r) == [FAIL, FAIL] and "-9 to -5 LUFS" in r[0].message


def test_length_per_mix(export, config):
    good = export("Plan Length", extended_seconds=390, radio_seconds=180)
    assert levels(master_length.run(ctx_with(good, config, "tgp-tech-house"))) == [PASS, PASS]
    short = export("Odd Lengths", extended_seconds=200, radio_seconds=100)
    assert levels(master_length.run(ctx_with(short, config, "tgp-tech-house"))) == [FAIL, FAIL]


@pytest.mark.parametrize("profile, radio_needed", [("edmgp-tech-house", True), ("tgp-tech-house", False),
                                                   ("hot-tech-house", False)])
def test_radio_mix_per_website(export, config, profile, radio_needed):
    r = mixes_present.run(ctx_with(export("No Radio", radio_seconds=0), config, profile))
    assert levels(r) == ([FAIL] if radio_needed else [PASS])


def test_report_has_the_website_checklist(export, config):
    run = engine.check(export(), config, profile="hot-tech-house", history=False)
    md = run.report.to_markdown()
    assert "- Website: House of Tracks" in md
    assert "## Before you upload to House of Tracks" in md and "- [ ] Three folders" in md
    assert run.report.count(FAIL)   # the fixtures are 16-bit, HoT wants 24
