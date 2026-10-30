from qabot.report import FAIL, PASS, WARN, Report, Result, add_to_history, load_history, runs_for


def report(*levels):
    r = Report(title="Song", profile="EDM GP: Tech House", folder="D:/x", version="0.1.0")
    r.results = [Result(f"check_{i}", lv, f"message {i}", "fix it" if lv != PASS else "", files=["a.wav"])
                 for i, lv in enumerate(levels)]
    return r


def test_overall_and_exit_codes():
    assert report(PASS, PASS).exit_code() == 0
    assert report(PASS, WARN).exit_code() == 1
    assert report(WARN, FAIL, PASS).exit_code() == 2
    assert report(WARN, FAIL, PASS).summary() == "FAIL: 1 fail, 1 warn, 1 pass"


def test_markdown_has_table_and_qa_block():
    md = report(PASS, FAIL).to_markdown()
    assert md.startswith("# QA REPORT: Song")
    assert "| ❌ | `check_1` | message 1 | fix it |" in md
    assert "## For qa.md" in md and "- [ ] FAIL check_1: message 1" in md and "- [x] PASS check_0" in md


def test_history(tmp_path):
    path = tmp_path / "history.json"
    add_to_history(path, report(FAIL))
    add_to_history(path, report(PASS))
    runs = load_history(path)
    assert [r["overall"] for r in runs_for(runs, "song")] == [FAIL, PASS]
    assert runs[0]["fails"] == ["check_0"]
