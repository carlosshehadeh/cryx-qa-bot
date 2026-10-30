"""Main window: drop zone, profile and track fields, results list with a
detail read-out, and the Run / Build / Copy / Open buttons."""

import html
import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QSplitter, QTextBrowser,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from qabot import APP_NAME, __version__, engine, package, rules
from qabot.report import FAIL, LEVELS, WARN
from qabot.scan import title_from_folder
from ui import theme
from ui.history_dialog import HistoryDialog
from ui.settings_dialog import SettingsDialog


class Worker(QThread):
    """Runs a function off the UI thread; reports progress, result or error."""
    progress = Signal(int, int, str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(self.progress.emit))
        except package.Refused as e:
            self.failed.emit(str(e))
        except Exception as e:  # shown to Carlos in plain words, never a crash
            self.failed.emit(f"{type(e).__name__}: {e}")


class DropZone(QFrame):
    """Big target for the export folder. Click to browse."""
    folderDropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drop")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(86)
        v = QVBoxLayout(self)
        self.big = QLabel("Drop your export folder here")
        f = QFont(self.big.font())
        f.setPixelSize(18)
        f.setBold(True)
        self.big.setFont(f)
        self.small = QLabel("or click to choose it. Your files are only read, never changed.")
        for w in (self.big, self.small):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(w)
        self._style(False)

    def _style(self, hot):
        border = theme.ACCENT if hot else "#3a3d44"
        self.setStyleSheet(f"QFrame#drop {{ background: #121316; border: 2px dashed {border}; border-radius: 6px; }}"
                           f" QLabel {{ color: {theme.LCD_TEXT}; background: transparent; }}")

    def set_folder(self, folder, summary=""):
        self.big.setText(Path(folder).name)
        self.small.setText(summary or str(folder))

    @staticmethod
    def _folder(event):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        for p in paths:
            if p.is_dir():
                return p
            if p.is_file():
                return p.parent
        return None

    def dragEnterEvent(self, event):
        if self._folder(event):
            self._style(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._style(False)

    def dropEvent(self, event):
        self._style(False)
        folder = self._folder(event)
        if folder:
            event.acceptProposedAction()
            self.folderDropped.emit(str(folder))

    def mousePressEvent(self, event):
        folder = QFileDialog.getExistingDirectory(self, "Choose the export folder")
        if folder:
            self.folderDropped.emit(folder)


def _hw(text):
    b = QPushButton(text.upper())
    b.setObjectName("hw")
    return b


def _led_box(text, checked):
    c = QCheckBox(text.upper())
    c.setObjectName("ledbox")
    c.setChecked(checked)
    return c


class MainWindow(QMainWindow):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.folder = None
        self.run = None
        self.worker = None
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(1100, 760)
        self.setAcceptDrops(True)
        self._build()
        self._load_profiles()
        self._update_buttons()

    # -- layout -----------------------------------------------------------
    def _build(self):
        central = theme.Faceplate()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(theme.Faceplate.CHEEK + 12, 10, theme.Faceplate.CHEEK + 12, 8)

        top = QHBoxLayout()
        top.addWidget(theme.Wordmark())
        top.addSpacing(12)
        self.site = QComboBox()
        self.site.setObjectName("lcd")
        self.site.setMinimumWidth(190)
        self.site.currentIndexChanged.connect(self._site_changed)
        self.profile = QComboBox()
        self.profile.setObjectName("lcd")
        self.profile.setMinimumWidth(190)
        self.profile.currentIndexChanged.connect(self._profile_changed)
        self.title = QLineEdit()
        self.title.setObjectName("lcd")
        self.title.setPlaceholderText("Track title (from the folder name)")
        self.bpm = QDoubleSpinBox()
        self.bpm.setObjectName("lcd")
        self.bpm.setRange(40, 250)
        self.bpm.setDecimals(1)
        self.bpm.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.key = QLineEdit()
        self.key.setObjectName("lcd")
        self.key.setPlaceholderText("e.g. F min")
        self.key.setMaximumWidth(90)
        for label, w, stretch in (("Website", self.site, 0), ("Genre", self.profile, 0), ("Track title", self.title, 1),
                                  ("BPM", self.bpm, 0), ("Key", self.key, 0)):
            top.addWidget(theme.column(theme.caps(label), w), stretch)
        top.addSpacing(8)
        self.history_btn = _hw("History")
        self.history_btn.clicked.connect(self.show_history)
        self.settings_btn = _hw("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        top.addWidget(theme.column(theme.caps(" "), self.history_btn))
        top.addWidget(theme.column(theme.caps(" "), self.settings_btn))
        outer.addLayout(top)

        screen = QFrame()
        screen.setObjectName("screen")
        sv = QVBoxLayout(screen)
        sv.setContentsMargins(10, 10, 10, 10)
        self.drop = DropZone()
        self.drop.folderDropped.connect(self.set_folder)
        sv.addWidget(self.drop)

        self.summary = QLabel("")
        f = QFont(self.summary.font())
        f.setPixelSize(15)
        f.setBold(True)
        self.summary.setFont(f)
        sv.addWidget(self.summary)

        split = QSplitter(Qt.Orientation.Vertical)
        self.results = QTreeWidget()
        self.results.setObjectName("results")
        self.results.setHeaderLabels(["", "CHECK", "RESULT"])
        self.results.setRootIsDecorated(False)
        self.results.setAlternatingRowColors(True)
        self.results.setUniformRowHeights(True)
        hdr = self.results.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(0, 72)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.results.currentItemChanged.connect(self._show_detail)
        self.detail = QTextBrowser()
        self.detail.setObjectName("detail")
        self.detail.setOpenExternalLinks(False)
        split.addWidget(self.results)
        split.addWidget(self.detail)
        split.setSizes([420, 180])
        sv.addWidget(split, 1)
        outer.addWidget(screen, 1)

        row = QHBoxLayout()
        self.run_btn = QPushButton("RUN CHECKS")
        self.run_btn.setObjectName("big")
        self.run_btn.clicked.connect(self.run_checks)
        self.build_btn = QPushButton("BUILD BUYER ZIP")
        self.build_btn.setObjectName("big")
        self.build_btn.clicked.connect(self.build_zip)
        self.copy_btn = _hw("Copy report for qa.md")
        self.copy_btn.clicked.connect(self.copy_report)
        self.open_btn = _hw("Open output folder")
        self.open_btn.clicked.connect(self.open_output)
        self.project_box = _led_box("Include project", self.config.include_project)
        self.mp3_box = _led_box("Make MP3s", self.config.mp3)
        for w in (self.run_btn, self.build_btn, self.copy_btn, self.open_btn):
            row.addWidget(w)
        row.addSpacing(10)
        row.addWidget(self.project_box)
        row.addWidget(self.mp3_box)
        row.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(180)
        self.progress.setVisible(False)
        row.addWidget(self.progress)
        outer.addLayout(row)

        self.setCentralWidget(central)
        self.statusBar().showMessage(f"Data folder: {self.config.rules_dir().parent}")

    def _load_profiles(self, keep=None):
        """Website picker first, then the genres that website has a rules file for."""
        self.catalog = rules.catalog(self.config.rules_dir())
        want = keep or self.config.default_profile
        site = self.catalog.get(want, {}).get("marketplace")
        self.site.blockSignals(True)
        self.site.clear()
        for name in rules.marketplaces(self.config.rules_dir()):
            self.site.addItem(name, name)
        self.site.setCurrentIndex(max(0, self.site.findData(site)))
        self.site.blockSignals(False)
        self._site_changed(keep=want)

    def _site_changed(self, *_, keep=None):
        site = self.site.currentData()
        current = keep or self.profile.currentData()
        genre = self.catalog.get(current, {}).get("genre")
        self.profile.blockSignals(True)
        self.profile.clear()
        for pid, p in self.catalog.items():
            if p["marketplace"] == site:
                self.profile.addItem(p["genre"], pid)
        i = self.profile.findData(current)
        if i < 0:   # same genre on the new website, if it has one
            i = next((n for n in range(self.profile.count())
                      if self.catalog[self.profile.itemData(n)]["genre"] == genre), 0)
        self.profile.setCurrentIndex(i)
        self.profile.blockSignals(False)
        self._profile_changed()

    def _profile_changed(self, *_):
        pid = self.profile.currentData()
        if not pid:
            return
        try:
            self.bpm.setValue(float(rules.load(pid, self.config.rules_dir()).get("bpm", 120)))
        except (OSError, ValueError):
            pass

    # -- window-wide drop ---------------------------------------------------
    def dragEnterEvent(self, event):
        if DropZone._folder(event):
            event.acceptProposedAction()

    def dropEvent(self, event):
        folder = DropZone._folder(event)
        if folder:
            self.set_folder(str(folder))

    # -- actions ------------------------------------------------------------
    def set_folder(self, folder):
        self.folder = Path(folder)
        self.title.setText(title_from_folder(self.folder.name, self.config.export_suffix))
        self.drop.set_folder(self.folder)
        self.run = None
        self.results.clear()
        self.detail.clear()
        self.summary.setText("")
        self.run_checks()

    def _busy(self):
        return self.worker is not None and self.worker.isRunning()

    def _start(self, fn, on_done, label):
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.statusBar().showMessage(label)
        self.worker = Worker(fn, self)
        self.worker.progress.connect(self._progress)
        self.worker.done.connect(on_done)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self._finished)
        self._update_buttons()
        self.worker.start()

    def _progress(self, i, n, what):
        self.progress.setRange(0, n)
        self.progress.setValue(i)
        self.statusBar().showMessage(f"{i}/{n}  {what}")

    def _finished(self):
        self.progress.setVisible(False)
        self._update_buttons()

    def _failed(self, message):
        self.statusBar().showMessage(message)
        QMessageBox.warning(self, APP_NAME, message)

    def run_checks(self):
        if not self.folder or self._busy():
            return
        folder, cfg = self.folder, self.config
        profile, bpm = self.profile.currentData(), self.bpm.value()
        title, key = self.title.text().strip() or None, self.key.text().strip()
        include = self.project_box.isChecked()

        def job(progress):
            return engine.check(folder, cfg, profile=profile, bpm=bpm, title=title, key=key,
                                include_project=include, progress=progress)
        self._start(job, self._checked, "Checking…")

    def _checked(self, run):
        self.run = run
        self.show_results(run.report)
        self.statusBar().showMessage(f"Checked {run.export.title}: {run.report.summary()}")

    def show_results(self, report):
        self.results.clear()
        order = sorted(report.results, key=lambda r: -LEVELS.index(r.level))
        for r in order:
            item = QTreeWidgetItem(["", r.check_id, r.message])
            item.setIcon(0, theme.led_icon(theme.LEVEL_COLOURS[r.level]))
            item.setText(0, r.level)
            item.setForeground(0, Qt.GlobalColor.white)
            item.setData(0, Qt.ItemDataRole.UserRole, r)
            item.setToolTip(2, r.message)
            self.results.addTopLevelItem(item)
        colour = theme.LEVEL_COLOURS[report.overall]
        self.summary.setText(f"<span style='color:{colour}'>{report.summary()}</span>")
        if self.results.topLevelItemCount():
            self.results.setCurrentItem(self.results.topLevelItem(0))

    def _show_detail(self, item, _previous=None):
        if not item:
            self.detail.clear()
            return
        r = item.data(0, Qt.ItemDataRole.UserRole)
        colour = theme.LEVEL_COLOURS[r.level]
        parts = [f"<p><b style='color:{colour}'>{r.level}</b> &nbsp; <b>{html.escape(r.check_id)}</b></p>",
                 f"<p>{html.escape(r.message)}</p>"]
        if r.fix:
            fix = re.sub(r" (\d\)) ", r"<br>\1 ", html.escape(r.fix))
            parts.append(f"<p><b>What to do:</b> {fix}</p>")
        if r.numbers:
            rows = "".join(f"<tr><td style='color:#8b94a5;padding-right:12px'>{html.escape(str(k))}</td>"
                           f"<td>{html.escape(str(v))}</td></tr>" for k, v in r.numbers.items())
            parts.append(f"<table>{rows}</table>")
        if r.files:
            parts.append("<ul>" + "".join(f"<li>{html.escape(f)}</li>" for f in r.files) + "</ul>")
        self.detail.setHtml("".join(parts))

    def build_zip(self):
        if not self.run or self._busy():
            return
        report = self.run.report
        if report.count(FAIL):
            return
        if report.count(WARN):
            warns = "\n".join(f"• {r.message}" for r in report.results if r.level == WARN)
            box = QMessageBox(QMessageBox.Icon.Question, APP_NAME,
                              f"{report.count(WARN)} warning(s):\n\n{warns}\n\nBuild the buyer zip anyway?",
                              parent=self)
            ok = box.addButton("I checked these", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is not ok:
                return
        run, cfg = self.run, self.config
        include, make_mp3 = self.project_box.isChecked(), self.mp3_box.isChecked()
        bitrate = run.rules.get("mp3", {}).get("bitrate_kbps", 320)

        def job(progress):
            return package.build(run.export, cfg, run.report, include_project=include, make_mp3=make_mp3,
                                 warnings_ok=True, bitrate=bitrate, progress=progress)
        self._start(job, self._built, "Building the buyer folder and zip…")

    def _built(self, built):
        self.statusBar().showMessage(f"Built {built.zip.name} ({built.files} files). Report: {built.report.name}")
        QMessageBox.information(self, APP_NAME, f"Done: {built.zip}\n\nReport (stays with you): {built.report}")

    def copy_report(self):
        if self.run:
            QGuiApplication.clipboard().setText(self.run.report.to_markdown())
            self.statusBar().showMessage("Report copied. Paste it into the track's qa.md.")

    def output_folder(self):
        if self.run:
            return package.output_root(self.run.export, self.config)
        return self.folder.parent if self.folder else None

    def open_output(self):
        folder = self.output_folder()
        if folder and folder.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            dlg.apply(self.config)
            self.config.save()
            self.project_box.setChecked(self.config.include_project)
            self.mp3_box.setChecked(self.config.mp3)
            self._load_profiles()
            if self.folder:
                self.run_checks()

    def show_history(self):
        HistoryDialog(self.config.history_path(), self.title.text().strip(), self).exec()

    def _update_buttons(self):
        busy = self._busy()
        has_run = self.run is not None
        fails = has_run and self.run.report.count(FAIL) > 0
        self.run_btn.setEnabled(bool(self.folder) and not busy)
        self.build_btn.setEnabled(has_run and not fails and not busy)
        self.build_btn.setToolTip("Fix the FAILs first" if fails else "")
        self.copy_btn.setEnabled(has_run)
        self.open_btn.setEnabled(bool(self.folder))
        self.project_box.setEnabled(not busy)

    def closeEvent(self, event):
        if self._busy():
            self.worker.wait(30000)
        super().closeEvent(event)
