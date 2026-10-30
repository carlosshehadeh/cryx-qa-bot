import hashlib
import zipfile

import pytest

from qabot import clean, engine, package
from qabot.report import FAIL, WARN


def hashes(folder):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob("*")) if p.is_file()}


def good_run(folder, config, **kw):
    run = engine.check(folder, config, history=False, **kw)
    # The fixtures' fake masters don't meet the open master-peak question; treat warnings as checked.
    assert run.report.count(FAIL) == 0, run.report.to_markdown()
    return run


def test_build_buyer_zip(export, config):
    folder = export("Zip Track", metadata=True, private_file=True,
                    als_text="<Ableton><Path Value=\"Samples/Imported/hit.wav\"/></Ableton>")
    before = hashes(folder)
    run = good_run(folder, config, include_project=True)
    built = package.build(run.export, config, run.report, include_project=True, warnings_ok=True)

    assert built.zip.name == "Zip Track BUYER.zip" and built.report.name == "Zip Track QA REPORT.md"
    with zipfile.ZipFile(built.zip) as z:
        names = z.namelist()
    root = "Zip Track BUYER/"
    assert root + "Zip Track (Extended Mix).wav" in names and root + "Zip Track (Extended Mix).mp3" in names
    assert root + "Zip Track (Radio Mix).mp3" in names
    assert root + "Stems Extended/05 Bass Sub.wav" in names
    assert root + "Project/Zip Track.als" in names
    assert not any(n.endswith("Main.wav") for n in names)
    assert not any("License" in n or n.endswith(".md") or n.endswith(".pdf") for n in names)
    assert not any("QA REPORT" in n for n in names)
    for wav in built.folder.rglob("*.wav"):
        assert clean.chunk_ids(wav) == ["fmt ", "data"]
    assert hashes(folder) == before   # originals never touched


def test_refuses_with_fails(export, config):
    run = engine.check(export("Missing Pump", missing_pump=True), config, history=False)
    with pytest.raises(package.Refused, match="failed"):
        package.build(run.export, config, run.report, warnings_ok=True)


def test_warnings_need_a_click(export, config):
    run = good_run(export(), config)
    assert run.report.count(WARN)
    with pytest.raises(package.Refused, match="warnings"):
        package.build(run.export, config, run.report)


def test_no_mp3_and_project_left_out(export, config):
    run = good_run(export("With Project", als_text="<Ableton/>"), config)
    built = package.build(run.export, config, run.report, make_mp3=False, warnings_ok=True)
    names = zipfile.ZipFile(built.zip).namelist()
    assert not any(n.endswith(".mp3") for n in names)
    assert not any("/Project/" in n for n in names)


def test_zip_is_checked_again(export, config, monkeypatch):
    """Even if the plan were wrong, Main.wav never ends up in the zip."""
    run = good_run(export(), config)
    real_plan = package.plan

    def leaky(ex, cfg, *a, **kw):
        p = real_plan(ex, cfg, *a, **kw)
        main = ex.stem_set("Extended").main
        p.items.append(package.Item(main, "Stems Extended/Main.wav", "wav"))
        return p
    monkeypatch.setattr(package, "plan", leaky)
    with pytest.raises(package.Refused, match="Main"):
        package.build(run.export, config, run.report, warnings_ok=True)
    assert not (package.output_root(run.export, config) / "Good Track BUYER.zip").exists()


def test_output_folder_inside_export_is_refused(export, config):
    folder = export()
    run = good_run(folder, config)
    config.output_folder = str(folder)
    with pytest.raises(package.Refused, match="inside the export"):
        package.build(run.export, config, run.report, warnings_ok=True)
