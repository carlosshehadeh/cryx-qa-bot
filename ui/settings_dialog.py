"""Settings: banned words, default profile, output, MP3, folder name patterns, rules folder."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from qabot import rules
from qabot.config import data_dir

PATTERNS = [
    ("export_suffix", "Export folder ends with"),
    ("masters_folder", "Masters folder"),
    ("project_folder", "Project folder"),
    ("extended_pattern", "Extended master name contains"),
    ("radio_pattern", "Radio master name contains"),
    ("main_pattern", "Main file name (pattern)"),
]


def _lcd(widget):
    widget.setObjectName("lcd")
    return widget


class SettingsDialog(QDialog):
    """Edits the settings; apply(config) writes them back."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(640, 640)
        v = QVBoxLayout(self)

        v.addWidget(QLabel("<b>Banned words</b>: one per line. Your real name, old and new artist names, "
                           "email, Windows user folder (C:\\Users\\...). None of these may reach a buyer."))
        self.banned = _lcd(QPlainTextEdit("\n".join(config.banned_words)))
        self.banned.setMinimumHeight(110)
        v.addWidget(self.banned)

        form = QFormLayout()
        self.profile = _lcd(QComboBox())
        for pid, name in rules.profiles(config.rules_dir()).items():
            self.profile.addItem(name, pid)
        self.profile.setCurrentIndex(max(0, self.profile.findData(config.default_profile)))
        form.addRow("Default profile", self.profile)

        out = QWidget()
        oh = QHBoxLayout(out)
        oh.setContentsMargins(0, 0, 0, 0)
        self.output = _lcd(QLineEdit(config.output_folder))
        self.output.setPlaceholderText("next to the export folder")
        browse = QPushButton("Choose…")
        browse.clicked.connect(self._choose_output)
        oh.addWidget(self.output, 1)
        oh.addWidget(browse)
        form.addRow("Output folder", out)
        self.mp3 = QCheckBox("Make 320 kbps MP3s of the masters")
        self.mp3.setChecked(config.mp3)
        form.addRow("", self.mp3)
        self.project = QCheckBox("Include the Project folder in the buyer zip by default")
        self.project.setChecked(config.include_project)
        form.addRow("", self.project)

        form.addRow(QLabel("<b>Export folder layout</b>"))
        self.stems_ext = _lcd(QLineEdit(config.stems_folders.get("Extended", "")))
        self.stems_radio = _lcd(QLineEdit(config.stems_folders.get("Radio", "")))
        form.addRow("Extended stems folder", self.stems_ext)
        form.addRow("Radio stems folder", self.stems_radio)
        self.fields = {}
        for key, label in PATTERNS:
            self.fields[key] = _lcd(QLineEdit(getattr(config, key)))
            form.addRow(label, self.fields[key])
        v.addLayout(form)

        rules_row = QHBoxLayout()
        self.rules_dir = config.rules_dir()
        rules_row.addWidget(QLabel(f"Rules (one JSON per marketplace and genre): {self.rules_dir}"), 1)
        open_rules = QPushButton("Open rules folder")
        open_rules.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.rules_dir))))
        rules_row.addWidget(open_rules)
        v.addLayout(rules_row)
        v.addWidget(QLabel(f"Settings and history live in: {data_dir()}"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def _choose_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Where to put BUYER folders and zips")
        if folder:
            self.output.setText(folder)

    def apply(self, config):
        config.banned_words = [w.strip() for w in self.banned.toPlainText().splitlines() if w.strip()]
        config.default_profile = self.profile.currentData() or config.default_profile
        config.output_folder = self.output.text().strip()
        config.mp3 = self.mp3.isChecked()
        config.include_project = self.project.isChecked()
        config.stems_folders = {"Extended": self.stems_ext.text().strip() or "Stems Extended",
                                "Radio": self.stems_radio.text().strip() or "Stems Radio"}
        for key, _ in PATTERNS:
            text = self.fields[key].text()
            if key != "export_suffix":
                text = text.strip()
            if text or key == "export_suffix":
                setattr(config, key, text)
