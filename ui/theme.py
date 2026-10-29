"""Hardware look, shared with Cryx MIDI Vault: a dark slate faceplate with
wood cheeks around a dark screen, LCD read-outs and LED switches.

Everything is drawn with style sheets and a few small QPainter widgets, no
images, shadows or animations, so it costs nothing extra to run.
"""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

FACE = "#2a2f38"          # faceplate
FACE_DARK = "#1f232a"
INK = "#d9dde5"           # text on the faceplate
SCREEN = "#15181d"        # inner screen
SCREEN_LINE = "#2a2f38"
LCD = "#0c0d0f"
LCD_TEXT = "#ece9e1"
ACCENT = "#ff8a3d"        # orange
TEAL = "#3ccfc0"
DIM = "#8a8f99"
WOOD = "#4a3022"

LEVEL_COLOURS = {"PASS": "#4cd07d", "WARN": "#ffd166", "FAIL": "#ff5a4f"}

STYLE = f"""
QMainWindow, QDialog {{ background: {FACE}; }}
QWidget {{ color: {INK}; font-size: 12px; }}
QToolTip {{ background: {LCD}; color: {LCD_TEXT}; border: 1px solid {SCREEN_LINE}; padding: 4px; }}

/* faceplate labels: small caps like printed hardware legends */
QLabel[caps="true"] {{ color: #8b94a5; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}

/* hardware push buttons on the faceplate */
QPushButton#hw {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3c4350, stop:1 #2c323c);
    border: 1px solid #4b5262; border-radius: 3px; padding: 5px 12px;
    color: {INK}; font-size: 10px; font-weight: 700; letter-spacing: 1px;
}}
QPushButton#hw:hover {{ background: #454d5b; }}
QPushButton#hw:pressed {{ background: #232831; }}

/* LCD read-outs: search box, track fields, dropdowns */
QLineEdit#lcd, QComboBox#lcd, QDoubleSpinBox#lcd {{
    background: {LCD}; color: {LCD_TEXT}; border: 2px solid #3a3d44; border-radius: 4px;
    padding: 4px 8px; selection-background-color: {ACCENT}; selection-color: #111;
}}
QLineEdit#lcd[big="true"] {{ font-size: 16px; padding: 8px 12px; }}
QComboBox#lcd::drop-down {{ border: none; width: 18px; }}
QComboBox#lcd::down-arrow {{ image: url("@ARROW@"); width: 8px; height: 5px; }}
QDoubleSpinBox#lcd {{ min-width: 64px; }}
QDoubleSpinBox#lcd::up-button, QDoubleSpinBox#lcd::down-button {{
    width: 0px; height: 0px; border: none; subcontrol-origin: border;
}}
QComboBox#lcd QAbstractItemView {{
    background: {LCD}; color: {LCD_TEXT}; selection-background-color: {ACCENT}; selection-color: #111;
    border: 1px solid {SCREEN_LINE};
}}

/* the dark screen in the middle */
QFrame#screen {{ background: {SCREEN}; border: 2px solid #0d0e10; border-radius: 6px; }}
QFrame#screen QLabel {{ color: {LCD_TEXT}; }}
QFrame#screen QLabel[caps="true"] {{ color: #b9b6ae; }}
QFrame#divider {{ background: {SCREEN_LINE}; max-width: 1px; min-width: 1px; }}

/* filters on the screen */
QFrame#screen QComboBox#lcd {{ background: #121316; min-width: 84px; }}
QPushButton#led {{
    background: #26292f; color: #c9c6be; border: 1px solid #3a3d44; border-radius: 3px;
    padding: 4px 10px; font-size: 10px; font-weight: 700; letter-spacing: 1px;
}}
QPushButton#led:checked {{ color: #111; background: {ACCENT}; border-color: {ACCENT}; }}

/* results */
QTableView#results {{
    background: #16181b; alternate-background-color: #1a1c20; color: {LCD_TEXT};
    gridline-color: transparent; border: none; selection-background-color: {ACCENT};
    selection-color: #111;
}}
QTableView#results QHeaderView::section {{
    background: #202328; color: #b9b6ae; border: none; border-bottom: 1px solid {SCREEN_LINE};
    padding: 5px; font-size: 10px; font-weight: 700; letter-spacing: 1px;
}}
QScrollBar:vertical {{ background: #16181b; width: 10px; }}
QScrollBar::handle:vertical {{ background: #3a3d44; border-radius: 4px; min-height: 30px; }}
QScrollBar:horizontal {{ background: #16181b; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #3a3d44; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QSplitter::handle {{ background: {SCREEN_LINE}; height: 2px; }}

/* LED toggles on the faceplate (Loop, Sync, Play on select) */
QCheckBox#ledbox {{ font-size: 10px; font-weight: 700; letter-spacing: 1px; spacing: 6px; }}
QCheckBox#ledbox::indicator {{
    width: 10px; height: 10px; border-radius: 6px; border: 1px solid #14171c; background: #4a5160;
}}
QCheckBox#ledbox::indicator:checked {{ background: {ACCENT}; border-color: #c25a17; }}

QStatusBar {{ background: {FACE_DARK}; color: {INK}; }}
QProgressBar {{ background: {LCD}; border: 1px solid #3a3d44; border-radius: 3px; height: 10px; color: transparent; }}
QProgressBar::chunk {{ background: {ACCENT}; }}
QMenu {{ background: {LCD}; color: {LCD_TEXT}; border: 1px solid {SCREEN_LINE}; }}
QMenu::item:selected {{ background: {ACCENT}; color: #111; }}
QTableWidget {{ background: {LCD}; color: {LCD_TEXT}; }}

/* QA Bot: the results list and detail read-out */
QTreeWidget#results {{
    background: #16181b; alternate-background-color: #1a1c20; color: {LCD_TEXT}; border: none;
    selection-background-color: #2c3038; selection-color: {LCD_TEXT}; font-size: 12px;
}}
QTreeWidget#results QHeaderView::section {{
    background: #202328; color: #b9b6ae; border: none; border-bottom: 1px solid {SCREEN_LINE};
    padding: 5px; font-size: 10px; font-weight: 700; letter-spacing: 1px;
}}
QTextBrowser#detail {{ background: {LCD}; color: {LCD_TEXT}; border: none; padding: 8px; font-size: 12px; }}
QPushButton#hw:disabled {{ color: #5d6370; background: #262a31; border-color: #333844; }}
QPushButton#big {{
    background: {ACCENT}; color: #111; border: none; border-radius: 4px; padding: 9px 18px;
    font-size: 11px; font-weight: 800; letter-spacing: 1px;
}}
QPushButton#big:hover {{ background: #ff9d5c; }}
QPushButton#big:disabled {{ background: #4a3a30; color: #7d6a5c; }}
QPlainTextEdit#lcd {{ background: {LCD}; color: {LCD_TEXT}; border: 2px solid #3a3d44; border-radius: 4px; }}
"""


def stylesheet():
    """STYLE with the drop-down arrow image written to a temp file (style
    sheets can only load images from files)."""
    import os
    import tempfile
    from PySide6.QtGui import QImage, QPolygonF
    path = os.path.join(tempfile.gettempdir(), "cryx_qa_arrow.png")
    if not os.path.exists(path):
        img = QImage(16, 10, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(DIM))
        p.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(16, 0), QPointF(8, 10)]))
        p.end()
        img.save(path)
    return STYLE.replace("@ARROW@", path.replace("\\", "/"))


def _round_pen(colour, width):
    pen = QPen(QColor(colour), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def caps(text):
    label = QLabel(text.upper())
    label.setProperty("caps", True)
    return label


class Faceplate(QWidget):
    """The window body: brushed light panel with wooden side cheeks."""

    CHEEK = 10

    def paintEvent(self, event):
        p = QPainter(self)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#323844"))
        g.setColorAt(1, QColor(FACE_DARK))
        p.fillRect(self.rect(), g)
        wood = QLinearGradient(0, 0, self.CHEEK, 0)
        wood.setColorAt(0, QColor("#2e1d14"))
        wood.setColorAt(1, QColor(WOOD))
        p.fillRect(0, 0, self.CHEEK, self.height(), wood)
        p.fillRect(self.width() - self.CHEEK, 0, self.CHEEK, self.height(), wood)


class Wordmark(QWidget):
    """'cryx' in big lower case with 'qa bot' tucked under it."""

    def sizeHint(self):
        return QSize(170, 54)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        big = QFont(self.font())
        big.setPixelSize(34)
        big.setWeight(QFont.Weight.DemiBold)
        big.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -1)
        p.setFont(big)
        p.setPen(QColor(INK))
        p.drawText(QRectF(2, -4, 170, 40), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "cryx")
        small = QFont(self.font())
        small.setPixelSize(13)
        p.setFont(small)
        p.setPen(QColor("#8b94a5"))
        p.drawText(QRectF(52, 30, 170, 20), Qt.AlignmentFlag.AlignLeft, "qa bot")
        p.setPen(QPen(QColor(INK), 2))
        p.drawLine(QPointF(4, 50), QPointF(48, 50))


def led_icon(colour, size=12):
    """A round LED in the given colour (results list)."""
    from PySide6.QtGui import QIcon, QPixmap
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#14171c"), 1))
    p.setBrush(QColor(colour))
    p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    p.end()
    return QIcon(pm)


def column(*widgets, spacing=4):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(spacing)
    for x in widgets:
        v.addWidget(x)
    return w
