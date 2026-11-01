"""Draws the DocuBhai Aristocrat Reader icon (red tile, white ribbon 'D') to icon.png / icon.ico,
and the three checkbox images (off / on / partial) the desktop stylesheet uses, to assets/."""
import math
import os
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF

N = 256


def stem_and_bowl():
    c = QPainterPath(QPointF(86, 196))
    c.cubicTo(92, 150, 82, 96, 90, 58)       # up the stem
    c.cubicTo(236, 26, 250, 196, 112, 188)   # over the top, round the bowl, back to the base
    return c


def swoosh():
    c = QPainterPath(QPointF(30, 214))
    c.cubicTo(88, 186, 140, 234, 226, 200)
    return c


def ribbon(path, width):
    """Polygon around `path` whose half-width at fraction t is width(t)."""
    n, left, right = 160, [], []
    for i in range(n + 1):
        t = i / n
        pt, ang = path.pointAtPercent(t), math.radians(path.angleAtPercent(t))
        nx, ny = -math.sin(ang), -math.cos(ang)  # unit normal (Qt angles are counter-clockwise)
        w = width(t)
        left.append(QPointF(pt.x() + nx * w, pt.y() + ny * w))
        right.append(QPointF(pt.x() - nx * w, pt.y() - ny * w))
    return QPolygonF(left + right[::-1])


def draw():
    img = QImage(N, N, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    # red rounded tile with a light top-to-bottom gradient
    g = QLinearGradient(0, 0, 0, N)
    g.setColorAt(0, QColor("#E8262F"))
    g.setColorAt(1, QColor("#B30D17"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(8, 8, N - 16, N - 16), 44, 44)
    # ribbon-style D: a stem+bowl stroke plus a flowing swoosh underneath; widths swell and taper
    shape = QPainterPath()
    shape.setFillRule(Qt.WindingFill)  # overlaps merge instead of cutting holes
    shape.addPolygon(ribbon(stem_and_bowl(), lambda t: 6 + 7 * min(1, t * 6, (1 - t) * 3) ** 0.6))
    shape.addPolygon(ribbon(swoosh(), lambda t: 2 + 6 * math.sin(math.pi * t) ** 0.8))
    p.setBrush(Qt.white)
    p.drawPath(shape)
    p.end()
    return img


def checkbox(state):
    """32px checkbox image: state is 'off', 'on' (tick) or 'partial' (dash)."""
    img = QImage(32, 32, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor("#6B6B6B"), 3))
    p.setBrush(Qt.white)
    p.drawRect(QRectF(3, 3, 26, 26))
    p.setPen(QPen(QColor("black"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if state == "on":
        p.drawPolyline(QPolygonF([QPointF(9, 17), QPointF(14, 22), QPointF(23, 10)]))
    elif state == "partial":
        p.drawLine(9, 16, 23, 16)
    p.end()
    return img


if __name__ == "__main__":
    QGuiApplication(sys.argv)
    img = draw()
    img.save("icon.png")
    img.save("icon.ico")
    os.makedirs("assets", exist_ok=True)
    for state in ("off", "on", "partial"):
        checkbox(state).save(f"assets/checkbox-{state}.png")
