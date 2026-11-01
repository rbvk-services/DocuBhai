import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest  # noqa: E402
from pypdf import PdfReader  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import app as docu  # noqa: E402
from test_pdf_ops import make_pdf  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(docu.STYLE)
    return a


def test_window_has_four_tabs(qapp):
    w = docu.MainWindow()
    assert [w.tabs.tabText(i) for i in range(4)] == ["Merge", "Split", "Sign", "Compare"]
    assert "Comic Sans" in docu.STYLE


def test_merge_through_gui_with_reorder(qapp, tmp_path):
    a = make_pdf(tmp_path / "a.pdf", ["A"])
    b = make_pdf(tmp_path / "b.pdf", ["B"])
    w = docu.MainWindow()
    t = w.merge_tab
    t.add_files([a, b])
    t.list.itemClicked.emit(t.list.item(1))  # tick B
    t.move(-1)  # B now first
    out = str(tmp_path / "m.pdf")
    t.do_merge(out)
    assert [p.extract_text().strip() for p in PdfReader(out).pages] == ["B", "A"]


def test_split_sign_compare_through_gui(qapp, tmp_path):
    src = make_pdf(tmp_path / "s.pdf", ["One", "Two"])
    w = docu.MainWindow()
    w.split_tab.src.edit.setText(src)
    w.split_tab.do_split(str(tmp_path / "o"))
    assert len(os.listdir(tmp_path / "o")) == 2

    w.sign_tab.src.edit.setText(src)
    w.sign_tab.text.setText("Me")
    signed = str(tmp_path / "signed.pdf")
    w.sign_tab.do_sign(signed)
    assert os.path.exists(signed)

    w.compare_tab.a.edit.setText(src)
    w.compare_tab.b.edit.setText(signed)
    w.compare_tab.do_compare()
    assert "+" in w.compare_tab.result.toPlainText()  # signature shows as a diff


def test_errors_do_not_crash(qapp, monkeypatch):
    shown = []
    monkeypatch.setattr(docu.QMessageBox, "critical", lambda *a: shown.append(a[2]))
    w = docu.MainWindow()
    w.run_safely(w.merge_tab.do_merge, "x.pdf")  # empty list -> ValueError
    assert shown and "Nothing to merge" in shown[0]


def test_window_uses_icon_and_title(qapp):
    w = docu.MainWindow()
    assert os.path.exists(docu.ICON) and not w.windowIcon().isNull()
    assert w.windowTitle() == "DocuBhai Aristocrat Reader"
