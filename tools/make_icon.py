"""Draw the app icon and write assets/icon.png and assets/icon.ico.

    python tools/make_icon.py
"""

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def draw(size):
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#16181d"))
    p.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 48 * s, 48 * s)
    # Level-meter bars and a tick: an abstract mark for "checked".
    p.setBrush(QColor("#ff8a3d"))
    for i, h in enumerate((70, 120, 160, 100, 136)):
        x = 40 + i * 30
        p.drawRoundedRect(QRectF(x * s, (208 - h) * s, 20 * s, h * s), 6 * s, 6 * s)
    tick = QPen(QColor("#4cd07d"), 22 * s)
    tick.setCapStyle(Qt.PenCapStyle.RoundCap)
    tick.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(tick)
    p.drawPolyline([QPointF(160 * s, 92 * s), QPointF(186 * s, 118 * s), QPointF(228 * s, 60 * s)])
    p.end()
    return img


def png_bytes(img):
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(data)


def main():
    QGuiApplication.instance() or QGuiApplication(sys.argv)
    ASSETS.mkdir(exist_ok=True)
    draw(256).save(str(ASSETS / "icon.png"))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [png_bytes(draw(n)) for n in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for n, data in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    (ASSETS / "icon.ico").write_bytes(header + entries + b"".join(images))
    print("wrote", ASSETS / "icon.png", ASSETS / "icon.ico")


if __name__ == "__main__":
    main()
