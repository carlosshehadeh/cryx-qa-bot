"""The null test, the most important check."""

from qabot.checks import null_test
from qabot.report import FAIL, PASS, WARN


def run(ctx):
    [r] = null_test.run(ctx)
    return r


def test_good_export_nulls(export, ctx_for):
    r = run(ctx_for(export()))
    assert r.level == PASS and r.numbers["residual_db"] < -100


def test_missing_pump_fails_and_names_the_bass(export, ctx_for):
    """Track one: sidechain on the bus, so the bass stems lack the pump."""
    r = run(ctx_for(export("Missing Pump", missing_pump=True)))
    assert r.level == FAIL
    assert "bars 9 to 16" in r.message
    assert set(r.numbers["suspects"]) >= {"05 Bass Sub", "06 Bass Mid"}
    assert r.files == ["Stems Extended/05 Bass Sub.wav", "Stems Extended/06 Bass Mid.wav"] or \
        r.files == ["Stems Extended/06 Bass Mid.wav", "Stems Extended/05 Bass Sub.wav"]
    assert r.fix.startswith("Likely causes: 1) Sidechain or effects on a bus")


def test_small_offset_is_found(export, ctx_for):
    r = run(ctx_for(export("Shifted", shift_main=10)))
    assert r.level == PASS and r.numbers["offset_samples"] == 10
    assert "10 samples early" in r.message


def test_master_rack_left_on(export, ctx_for):
    r = run(ctx_for(export("Rack On", rack_on=True)))
    assert r.level == FAIL
    assert "whole mix" in r.message and r.fix.startswith("Likely causes: 1) The master rack")


def test_missing_return_stem(export, ctx_for):
    r = run(ctx_for(export("No Delay", drop_stem="B Delay")))
    assert r.level in (WARN, FAIL)
    assert "doesn't match any stem" in r.message and "1) A stem is missing" in r.fix


def test_no_main(export, ctx_for):
    r = run(ctx_for(export("No Main", main=False)))
    assert r.level == FAIL and "Main.wav" in r.fix


def test_thresholds_come_from_the_rules(export, ctx_for):
    r = run(ctx_for(export("No Delay", drop_stem="B Delay"), null_test={"pass_db": -10, "fail_db": -5}))
    assert r.level == PASS
