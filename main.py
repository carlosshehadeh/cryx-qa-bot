"""Starts Cryx QA Bot (the window). The command line is cli.py."""

import sys

from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication

from qabot import APP_NAME
from qabot.config import Config, bundle_dir
from ui import theme
from ui.main_window import MainWindow


def hardware_palette():
    """Base colours under the style sheet in ui/theme.py."""
    p = QPalette()
    colours = {
        QPalette.ColorRole.Window: theme.FACE, QPalette.ColorRole.WindowText: theme.INK,
        QPalette.ColorRole.Base: theme.LCD, QPalette.ColorRole.AlternateBase: "#1a1c20",
        QPalette.ColorRole.Text: theme.LCD_TEXT, QPalette.ColorRole.Button: "#3a404c",
        QPalette.ColorRole.ButtonText: theme.INK, QPalette.ColorRole.Highlight: theme.ACCENT,
        QPalette.ColorRole.HighlightedText: "#111111", QPalette.ColorRole.ToolTipBase: theme.LCD,
        QPalette.ColorRole.ToolTipText: theme.LCD_TEXT, QPalette.ColorRole.PlaceholderText: "#7d828c",
        QPalette.ColorRole.Link: theme.ACCENT,
    }
    for role, c in colours.items():
        p.setColor(role, QColor(c))
    return p


def main(argv=None):
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setPalette(hardware_palette())
    app.setStyleSheet(theme.stylesheet())
    icon = bundle_dir() / "assets" / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    window = MainWindow(Config.load())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
