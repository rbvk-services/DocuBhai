import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import app as docu  # noqa: E402
from test_pdf_ops import make_pdf  # noqa: E402
from viewer import BASE, ViewTab  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def tab(qapp, tmp_path):
    t = ViewTab()
    t.resize(700, 500)
    t.show()
    t.load(make_pdf(tmp_path / "v.pdf", ["Hello viewer", "Second page", "Third page"]))
    QApplication.processEvents()
    return t


def test_loads_and_renders(tab):
    assert tab.doc.pageCount() == 3 and tab.of.text() == "of 3"
    assert not tab.view.image(0).isNull()


def test_page_background_is_opaque_white(tab):
    img = tab.view.image(0)
    px = img.pixelColor(2, 2)
    assert (px.red(), px.green(), px.blue(), px.alpha()) == (255, 255, 255, 255)


def test_renders_above_screen_resolution(tab):
    img = tab.view.image(0)
    assert img.devicePixelRatio() >= 2
    assert img.width() >= 2 * tab.view.sizes[0].width() - 1


def test_all_pages_stacked_and_cache_is_bounded(qapp, tmp_path):
    t = ViewTab()
    t.load(make_pdf(tmp_path / "big.pdf", [f"P{i}" for i in range(20)]))
    assert t.view.tops == sorted(t.view.tops) and len(t.view.tops) == 20
    for i in range(20):
        t.view.image(i)
    assert len(t.view.cache) <= 8


def test_continuous_scroll_updates_current_page(tab):
    bar = tab.scroll.verticalScrollBar()
    assert bar.maximum() > 0  # more than one screenful of content
    bar.setValue(bar.maximum())
    assert tab.page == 2 and tab.goto.value() == 3
    bar.setValue(0)
    assert tab.page == 0


def test_bad_file_raises(qapp, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("not a pdf")
    with pytest.raises(ValueError):
        ViewTab().load(str(bad))


def test_page_navigation_is_clamped(tab):
    tab.go_to(tab.page + 1)
    assert tab.page == 1 and tab.goto.value() == 2
    assert tab.scroll.verticalScrollBar().value() > 0
    tab.go_to(99)
    tab.go_to(-1)
    assert tab.page == 1
    tab.go_to(2)
    tab.go_to(tab.page + 1)  # past the end
    assert tab.page == 2


def test_zoom_in_out_and_limits(tab):
    w0 = tab.view.width()
    tab.zoom_by(1.25)
    assert tab.view.width() > w0 and tab.view.height() > 0 and tab.zoom_label.text() == "125%"
    tab.zoom_by(0.8)
    assert tab.zoom_label.text() == "100%"
    for _ in range(40):
        tab.zoom_by(2)
    assert tab.zoom_label.text() == "500%"
    for _ in range(40):
        tab.zoom_by(0.5)
    assert tab.zoom_label.text() == "25%"


def test_fit_width(tab):
    tab.resize(500, 400)
    tab.fit_width()
    assert tab.view.width() <= tab.scroll.viewport().width()


def test_select_and_copy_text(tab):
    # make_pdf draws text at PDF (100,700) on a A4 page (842pt tall) -> glyphs span x 101-165, y 133-142 from the top
    s, o = tab.scale, tab.view.page_rect(0).topLeft()

    def at(x, y):
        return QPoint(int(o.x() + x * s), int(o.y() + y * s))

    QTest.mousePress(tab.view, Qt.LeftButton, Qt.NoModifier, at(99, 137))
    QTest.mouseMove(tab.view, at(170, 137))
    QTest.mouseRelease(tab.view, Qt.LeftButton, Qt.NoModifier, at(170, 137))
    assert "Hello viewer" in tab.view.text()
    QGuiApplication.clipboard().clear()
    tab.copy()
    assert "Hello viewer" in QGuiApplication.clipboard().text()


def test_view_tab_in_main_window_and_black_text(qapp):
    w = docu.MainWindow()
    assert w.tabs.tabText(4) == "View"
    assert "color: black" in docu.STYLE.splitlines()[1]
    assert BASE == pytest.approx(1.333, abs=0.01)
