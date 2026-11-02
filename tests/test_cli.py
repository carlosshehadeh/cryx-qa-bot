from qabot import cli


def test_exit_codes(export, capsys):
    assert cli.main(["check", str(export("Missing Pump", missing_pump=True)), "--quiet"]) == 2
    assert capsys.readouterr().out.startswith("FAIL")
    assert cli.main(["check", str(export()), "--quiet"]) == 1   # open master-peak question = warning


def test_missing_folder(tmp_path):
    assert cli.main(["check", str(tmp_path / "nope")]) == 3


def test_profiles(capsys):
    assert cli.main(["profiles"]) == 0
    out = capsys.readouterr().out
    for pid in ("edmgp-tech-house", "edmgp-melodic-house-techno", "tgp-tech-house", "hot-melodic-house-techno"):
        assert pid in out


def test_build_from_command_line(export, tmp_path, capsys):
    report = tmp_path / "r.md"
    code = cli.main(["check", str(export("Cli Build")), "--build", "--ok-warnings", "--report", str(report)])
    assert code == 1 and report.exists()
    assert "Cli Build BUYER.zip" in capsys.readouterr().out
