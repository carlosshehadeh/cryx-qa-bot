"""Smoke tests for the window, run headless (QT_QPA_PLATFORM=offscreen)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from qabot.report import FAIL  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(app, config):
    from ui.main_window import MainWindow
    w = MainWindow(config)
    yield w
    w.close()


def wait(window):
    while window._busy():
        window.worker.wait(100)
        QtWidgets.QApplication.processEvents()
    QtWidgets.QApplication.processEvents()


def test_drop_runs_checks_and_blocks_zip_on_fail(window, export):
    assert not window.run_btn.isEnabled() and not window.build_btn.isEnabled()
    window.set_folder(str(export("Missing Pump", missing_pump=True)))
    wait(window)
    assert window.run and window.run.report.count(FAIL)
    assert window.title.text() == "Missing Pump"
    assert window.results.topLevelItemCount() == len(window.run.report.results)
    first = window.results.topLevelItem(0)
    assert first.text(0) == "FAIL"
    assert "What to do" in window.detail.toHtml()
    assert not window.build_btn.isEnabled() and window.copy_btn.isEnabled()


def test_good_folder_builds(window, export, monkeypatch):
    window.set_folder(str(export("Window Build")))
    wait(window)
    assert window.build_btn.isEnabled()
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", lambda self: self.setProperty("x", 1) or 0)
    monkeypatch.setattr(QtWidgets.QMessageBox, "clickedButton", lambda self: self.buttons()[0])
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    window.mp3_box.setChecked(False)
    window.build_zip()
    wait(window)
    out = window.output_folder()
    assert (out / "Window Build BUYER.zip").exists()


def test_settings_dialog_round_trip(app, config):
    from ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(config)
    dlg.banned.setPlainText("Real Name\n\nold@mail.com ")
    dlg.mp3.setChecked(False)
    dlg.apply(config)
    assert config.banned_words == ["Real Name", "old@mail.com"] and config.mp3 is False


def test_history_dialog(app, tmp_path):
    from qabot.report import Report, add_to_history
    from ui.history_dialog import HistoryDialog
    path = tmp_path / "h.json"
    add_to_history(path, Report("Song", "p", "f", "0.1.0"))
    add_to_history(path, Report("Other", "p", "f", "0.1.0"))
    dlg = HistoryDialog(path, "Song")
    assert dlg.table.rowCount() == 1
    dlg.only.setChecked(False)
    assert dlg.table.rowCount() == 2
