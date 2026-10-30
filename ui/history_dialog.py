"""Past runs from history.json, so a track's way from FAIL to PASS is visible."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from qabot.report import load_history, runs_for
from ui import theme

COLUMNS = [("date", "Date"), ("title", "Track"), ("profile", "Profile"), ("overall", "Result"),
           ("fail", "Fail"), ("warn", "Warn"), ("pass", "Pass"), ("fails", "Failed checks")]


class HistoryDialog(QDialog):
    def __init__(self, path, title="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run history")
        self.resize(900, 420)
        self.runs = load_history(path)
        self.title = title
        v = QVBoxLayout(self)
        self.only = QCheckBox(f"Only '{title}'" if title else "Only this track")
        self.only.setChecked(bool(title))
        self.only.setEnabled(bool(title))
        self.only.toggled.connect(self.fill)
        v.addWidget(self.only)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([c for _, c in COLUMNS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        v.addWidget(self.table)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)
        self.fill()

    def fill(self, *_):
        runs = runs_for(self.runs, self.title) if self.only.isChecked() else self.runs
        runs = list(reversed(runs))
        self.table.setRowCount(len(runs))
        for i, r in enumerate(runs):
            for j, (key, _) in enumerate(COLUMNS):
                value = r.get(key, "")
                item = QTableWidgetItem(", ".join(value) if isinstance(value, list) else str(value))
                if key == "overall":
                    item.setForeground(QColor(theme.LEVEL_COLOURS.get(value, theme.LCD_TEXT)))
                self.table.setItem(i, j, item)
