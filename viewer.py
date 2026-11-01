"""PDF viewer tab: continuous scroll, zoom, page navigation, text selection and copy (QtPdf)."""
from bisect import bisect_right
from collections import OrderedDict
from math import sqrt

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QKeySequence, QPainter, QShortcut
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)

BASE = 96 / 72  # px per PDF point at 100% zoom
MIN_ZOOM, MAX_ZOOM = 0.25, 5.0
MARGIN = GAP = 10  # px around / between pages
DESK = QColor("#808080")  # the "desk" the white pages lie on
CACHE_PAGES = 8
MAX_PIXELS = 16_000_000  # cap on one rendered page so huge zooms don't eat memory


class PageView(QWidget):
    """All pages stacked vertically. Only pages in the paint region are rendered (and cached)."""
    zoomWheel = Signal(int)  # +1 / -1 on Ctrl+wheel

    def __init__(self):
        super().__init__()
        self.doc, self.scale = None, BASE
        self.sizes, self.tops, self.maxw = [], [], 0.0
        self.cache = OrderedDict()
        self.sel = None    # (page, QPdfSelection)
        self.start = None  # (page, QPointF in PDF points)
        self.setCursor(Qt.IBeamCursor)

    def set_doc(self, doc, scale):
        self.doc = doc
        self.set_scale(scale)

    def set_scale(self, scale):
        """Re-layout every page at `scale` (cheap: sizes only, no rendering)."""
        self.scale, self.sel = scale, None
        self.cache.clear()
        self.sizes = [self.doc.pagePointSize(i) * scale for i in range(self.doc.pageCount())]
        self.maxw = max((s.width() for s in self.sizes), default=0.0)
        y, self.tops = MARGIN, []
        for s in self.sizes:
            self.tops.append(y)
            y += s.height() + GAP
        self.setFixedSize(int(self.maxw + 2 * MARGIN), int(y - GAP + MARGIN))
        self.update()

    def page_at(self, y):
        return max(0, min(len(self.tops) - 1, bisect_right(self.tops, y) - 1))

    def page_rect(self, i):
        s = self.sizes[i]
        return QRectF(MARGIN + (self.maxw - s.width()) / 2, self.tops[i], s.width(), s.height())

    def image(self, i):
        """Page i on an opaque white background, rendered at higher resolution than the screen needs."""
        if i in self.cache:
            self.cache.move_to_end(i)
            return self.cache[i]
        w, h = self.sizes[i].width(), self.sizes[i].height()
        q = max(2.0, self.devicePixelRatioF())  # supersample for crisp text
        q = max(1.0, min(q, sqrt(MAX_PIXELS / max(w * h, 1))))
        size = QSize(round(w * q), round(h * q))
        raw = self.doc.render(i, size)
        img = QImage(size, QImage.Format_RGB32)
        img.fill(Qt.white)
        p = QPainter(img)
        p.drawImage(0, 0, raw)
        p.end()
        img.setDevicePixelRatio(q)
        self.cache[i] = img
        while len(self.cache) > CACHE_PAGES:
            self.cache.popitem(last=False)
        return img

    def text(self):
        return self.sel[1].text() if self.sel else ""

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(e.rect(), DESK)
        if not self.tops:
            return
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        for i in range(self.page_at(e.rect().top()), self.page_at(e.rect().bottom()) + 1):
            r = self.page_rect(i)
            if r.bottom() < e.rect().top() or r.top() > e.rect().bottom():
                continue
            p.drawImage(r, self.image(i))
            if self.sel and self.sel[0] == i:
                p.setBrush(QColor(49, 106, 197, 90))
                p.setPen(Qt.NoPen)
                for poly in self.sel[1].bounds():
                    p.drawPolygon([r.topLeft() + QPointF(pt.x(), pt.y()) * self.scale for pt in poly])

    def to_points(self, pos, page):
        return (pos - self.page_rect(page).topLeft()) / self.scale

    def mousePressEvent(self, e):
        if self.tops:
            page = self.page_at(e.position().y())
            self.start, self.sel = (page, self.to_points(e.position(), page)), None
            self.update()

    def mouseMoveEvent(self, e):
        if self.start and self.doc:
            page, pt = self.start
            sel = self.doc.getSelection(page, pt, self.to_points(e.position(), page))
            if sel.isValid():  # pointer off the text keeps the last good selection
                self.sel = (page, sel)
                self.update()

    def mouseReleaseEvent(self, e):
        self.start = None

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.zoomWheel.emit(1 if e.angleDelta().y() > 0 else -1)
        else:
            e.ignore()  # let the scroll area scroll


class ViewTab(QWidget):
    def __init__(self, with_open=True):
        super().__init__()
        self.doc = QPdfDocument(self)
        self.page, self.scale, self._jumping = 0, BASE, False
        self.view = PageView()
        self.view.zoomWheel.connect(lambda d: self.zoom_by(1.25 if d > 0 else 0.8))
        self.scroll = QScrollArea()
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget { background: #808080; }")
        self.scroll.setWidget(self.view)
        self.scroll.verticalScrollBar().setSingleStep(40)
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.goto = QSpinBox()
        self.goto.setMinimum(1)
        self.goto.setKeyboardTracking(False)
        self.goto.editingFinished.connect(self.on_goto)
        self.of = QLabel("of 0")
        self.zoom_label = QLabel("100%")

        def btn(text, fn):
            b = QPushButton(text)
            b.setMinimumWidth(0)
            b.clicked.connect(fn)
            return b

        bar = QHBoxLayout()
        for w in (*([btn("Open...", lambda: self.open_dialog())] if with_open else []), btn("< Prev", lambda: self.go_to(self.page - 1)),
                  self.goto, self.of, btn("Next >", lambda: self.go_to(self.page + 1)),
                  btn("-", lambda: self.zoom_by(0.8)), self.zoom_label, btn("+", lambda: self.zoom_by(1.25)),
                  btn("Fit Width", self.fit_width), btn("Copy", self.copy)):
            bar.addWidget(w)
        bar.addStretch()
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.scroll)
        QShortcut(QKeySequence.Copy, self, activated=self.copy)

    def open_dialog(self):
        path = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF files (*.pdf)")[0]
        if path:
            self.load(path)

    def load(self, path):
        if self.doc.load(path) != QPdfDocument.Error.None_:
            raise ValueError(f"Could not open {path}")
        self._loaded()

    def load_bytes(self, data):
        """Open a PDF held in memory (e.g. a merge preview) without touching the disk."""
        self._buf = QBuffer()  # keep a reference: QPdfDocument reads from it lazily
        self._buf.setData(QByteArray(data))
        self._buf.open(QIODevice.ReadOnly)
        self.doc.load(self._buf)
        if self.doc.status() != QPdfDocument.Status.Ready:
            raise ValueError("Could not open the PDF data")
        self._loaded()

    def _loaded(self):
        self.goto.setMaximum(self.doc.pageCount())
        self.of.setText(f"of {self.doc.pageCount()}")
        self.view.set_doc(self.doc, self.scale)
        self.go_to(0)

    def scroll_to(self, y):
        self._jumping = True  # programmatic scroll: don't recompute the current page from it
        self.scroll.verticalScrollBar().setValue(int(y))
        self._jumping = False

    def go_to(self, page):
        """Jump so that `page` (0-based) is at the top of the window."""
        if self.doc.pageCount() and 0 <= page < self.doc.pageCount():
            self.page = page
            self.goto.setValue(page + 1)
            self.scroll_to(self.view.tops[page] - MARGIN)

    def on_scroll(self, value):
        """User scrolled: the current page is the one in the middle of the window."""
        if not self._jumping and self.view.tops:
            self.page = self.view.page_at(value + self.scroll.viewport().height() / 2)
            self.goto.setValue(self.page + 1)

    def on_goto(self):
        if self.goto.value() - 1 != self.page:  # editingFinished also fires on focus loss
            self.go_to(self.goto.value() - 1)

    def set_zoom(self, scale):
        self.scale = max(MIN_ZOOM * BASE, min(MAX_ZOOM * BASE, scale))
        self.zoom_label.setText(f"{round(self.scale / BASE * 100)}%")
        if not self.doc.pageCount():
            return
        v = self.view  # keep the same spot of the same page in view
        y = self.scroll.verticalScrollBar().value()
        i = v.page_at(y)
        frac = (y - v.tops[i]) / v.sizes[i].height()
        v.set_scale(self.scale)
        self.scroll_to(v.tops[i] + frac * v.sizes[i].height())

    def zoom_by(self, factor):
        self.set_zoom(self.scale * factor)

    def fit_width(self):
        if self.doc.pageCount():
            width = self.doc.pagePointSize(self.page).width()
            self.set_zoom((self.scroll.viewport().width() - 2 * MARGIN - 20) / width)

    def copy(self):
        if self.view.text():
            QGuiApplication.clipboard().setText(self.view.text())
