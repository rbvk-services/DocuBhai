import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest  # noqa: E402
from PySide6.QtCore import QModelIndex, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402
from pypdf import PdfReader  # noqa: E402

import app as docu  # noqa: E402
import pdf_ops  # noqa: E402
from test_pdf_ops import make_pdf  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(docu.STYLE)
    return a


@pytest.fixture
def tab(qapp):
    return docu.MergeTab()


@pytest.fixture
def files(tmp_path):
    return [make_pdf(tmp_path / f"{n}.pdf", [f"{n}1", f"{n}2"]) for n in "ABC"]


def ticks(t):
    return [c for _, c in t.entries()]


def names(t):
    return [os.path.basename(n)[0] for n in t.items()]


def click(t, row):  # what a mouse click on a row does
    t.list.itemClicked.emit(t.list.item(row))


def texts(pdf_bytes_or_path):
    return [p.extract_text().strip() for p in PdfReader(pdf_bytes_or_path).pages]


# ---------- list, ticks, select-all ----------

def test_starts_empty_with_nothing_to_act_on(tab):
    assert all(not tab.btn[k].isEnabled() for k in ("rm", "up", "down", "clear")) and not tab.all.isEnabled()
    assert tab.btn["add"].isEnabled() and tab.btn["go"].isEnabled()  # Merge stays clickable: it explains the problem
    assert tab.count.text() == "0 of 0 selected"


def test_ticks_are_on_the_right_hand_side(tab):
    assert tab.list.layoutDirection() == Qt.RightToLeft  # mirrors the check indicator to the right
    assert tab.btn["up"].toolTip() == "Move up" and tab.btn["down"].toolTip() == "Move down"
    assert tab.btn["up"].text() == "▲" and tab.btn["down"].text() == "▼"


def test_add_files_unticked_and_duplicates_allowed(tab, files):
    tab.add_files(files[:2])
    tab.add_files([files[0]])  # same file again is legitimate
    assert names(tab) == ["A", "B", "A"] and ticks(tab) == [False] * 3


def test_add_nothing_is_a_no_op(tab, files):
    tab.add_files(files)
    tab.add_files([])  # e.g. the file dialog was cancelled
    assert names(tab) == ["A", "B", "C"]


def test_row_click_toggles_and_toggles_back(tab, files):
    tab.add_files(files)
    click(tab, 1)
    assert ticks(tab) == [False, True, False] and tab.count.text() == "1 of 3 selected"
    click(tab, 1)
    assert ticks(tab) == [False] * 3


def test_multiselect(tab, files):
    tab.add_files(files)
    click(tab, 0)
    click(tab, 2)
    assert ticks(tab) == [True, False, True] and tab.count.text() == "2 of 3 selected"


def test_select_all_cycle_none_some_all(tab, files):
    tab.add_files(files)
    assert tab.all.checkState() == Qt.Unchecked
    click(tab, 0)
    assert tab.all.checkState() == Qt.PartiallyChecked
    tab.all.click()  # from partial -> everything
    assert ticks(tab) == [True] * 3 and tab.all.checkState() == Qt.Checked
    tab.all.click()  # from all -> nothing
    assert ticks(tab) == [False] * 3 and tab.all.checkState() == Qt.Unchecked


def test_ticking_every_row_by_hand_checks_select_all(tab, files):
    tab.add_files(files)
    for r in range(3):
        click(tab, r)
    assert tab.all.checkState() == Qt.Checked


# ---------- remove ----------

def test_remove_deletes_only_ticked_rows(tab, files):
    tab.add_files(files)
    click(tab, 0)
    click(tab, 2)
    tab.btn["rm"].click()
    assert names(tab) == ["B"] and ticks(tab) == [False]


def test_remove_is_disabled_until_something_is_ticked(tab, files):
    tab.add_files(files)
    assert not tab.btn["rm"].isEnabled()
    click(tab, 1)
    assert tab.btn["rm"].isEnabled()
    tab.remove_checked()  # also safe to call directly
    tab.remove_checked()  # nothing ticked any more -> no change, no error
    assert names(tab) == ["A", "C"]


def test_removing_everything_leaves_a_clean_empty_state(tab, files):
    tab.add_files(files)
    tab.all.click()
    tab.btn["rm"].click()
    assert names(tab) == [] and not tab.btn["clear"].isEnabled() and not tab.all.isEnabled()


# ---------- arrows ----------

def test_up_down_move_the_ticked_group_and_keep_ticks(tab, files):
    tab.add_files(files)
    click(tab, 2)
    tab.btn["up"].click()
    assert names(tab) == ["A", "C", "B"] and ticks(tab) == [False, True, False]
    tab.btn["up"].click()
    assert names(tab) == ["C", "A", "B"] and ticks(tab) == [True, False, False]
    tab.btn["down"].click()
    assert names(tab) == ["A", "C", "B"]


def test_arrows_grey_out_at_the_edges(tab, files):
    tab.add_files(files)
    assert not tab.btn["up"].isEnabled() and not tab.btn["down"].isEnabled()  # nothing ticked
    click(tab, 0)
    assert not tab.btn["up"].isEnabled() and tab.btn["down"].isEnabled()  # first row
    click(tab, 0)
    click(tab, 2)
    assert tab.btn["up"].isEnabled() and not tab.btn["down"].isEnabled()  # last row
    tab.all.click()
    assert not tab.btn["up"].isEnabled() and not tab.btn["down"].isEnabled()  # everything ticked


def test_arrow_clicks_at_the_edge_are_harmless_even_if_forced(tab, files):
    tab.add_files(files)
    click(tab, 0)
    tab.move(-1)
    assert names(tab) == ["A", "B", "C"]


def test_dragging_a_row_keeps_state_consistent(tab, files):
    tab.add_files(files)
    click(tab, 0)  # A ticked, at the top
    assert not tab.btn["up"].isEnabled()
    tab.list.model().moveRows(QModelIndex(), 0, 1, QModelIndex(), 3)  # what a drag-and-drop does: A to the end
    assert names(tab) == ["B", "C", "A"] and ticks(tab) == [False, False, True]
    assert tab.btn["up"].isEnabled() and not tab.btn["down"].isEnabled()  # buttons followed the drag


# ---------- clear ----------

def test_clear_asks_first_and_keeps_files_if_declined(tab, files, monkeypatch):
    asked = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: asked.append(a[2]) or QMessageBox.No)
    tab.add_files(files)
    tab.btn["clear"].click()
    assert asked == ["Remove all 3 files from the list?"] and names(tab) == ["A", "B", "C"]


def test_clear_empties_the_list_when_confirmed(tab, files, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    tab.add_files(files)
    click(tab, 1)
    tab.btn["clear"].click()
    assert names(tab) == [] and tab.count.text() == "0 of 0 selected"


def test_clear_on_an_empty_list_does_not_prompt(tab, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: pytest.fail("must not prompt"))
    tab.clear()


# ---------- preview ----------

def test_preview_merges_all_files_in_list_order(tab, files):
    tab.add_files(files)
    click(tab, 2)
    tab.btn["up"].click()
    tab.btn["up"].click()  # C, A, B
    data, pages = tab.build_preview()
    assert data[:5] == b"%PDF-" and pages == 6
    import io
    assert texts(io.BytesIO(data)) == ["C1", "C2", "A1", "A2", "B1", "B2"]


def test_ticks_do_not_change_what_is_previewed_or_merged(tab, files, tmp_path):
    tab.add_files(files)
    click(tab, 1)  # only B ticked
    _, pages = tab.build_preview()
    assert pages == 6  # all three files, not just the ticked one
    out = str(tmp_path / "m.pdf")
    tab.do_merge(out)
    assert texts(out) == ["A1", "A2", "B1", "B2", "C1", "C2"]


def test_preview_does_not_write_anything_to_disk(tab, files, tmp_path):
    tab.add_files(files)
    before = sorted(os.listdir(tmp_path))
    tab.build_preview()
    assert sorted(os.listdir(tmp_path)) == before


def test_preview_dialog_shows_the_merged_pdf(tab, files, qapp):
    tab.add_files(files[:2])
    data, pages = tab.build_preview()
    d = docu.PreviewDialog(data, 2, pages, tab)
    assert d.windowTitle() == "Merge preview - 2 files, 4 pages"
    assert d.view.doc.pageCount() == 4 and d.view.of.text() == "of 4"
    labels = [b.text() for b in d.view.findChildren(docu.QPushButton)]
    assert "Open..." not in labels and "Next >" in labels  # a preview has no Open button, but can still navigate


def test_preview_dialog_save_writes_identical_bytes(tab, files, tmp_path, qapp):
    tab.add_files(files)
    data, pages = tab.build_preview()
    out = tmp_path / "saved.pdf"
    docu.PreviewDialog(data, 3, pages, tab).save(str(out))
    assert out.read_bytes() == data


def test_preview_dialog_save_cancelled_writes_nothing(tab, files, tmp_path, monkeypatch, qapp):
    monkeypatch.setattr(docu.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))
    tab.add_files(files)
    data, pages = tab.build_preview()
    before = sorted(os.listdir(tmp_path))
    docu.PreviewDialog(data, 3, pages, tab).save()
    assert sorted(os.listdir(tmp_path)) == before


def test_do_preview_opens_the_dialog(tab, files, monkeypatch):
    opened = []
    monkeypatch.setattr(docu.PreviewDialog, "exec", lambda self: opened.append(self.windowTitle()))
    tab.add_files(files)
    tab.do_preview()
    assert opened == ["Merge preview - 3 files, 6 pages"]


# ---------- negative cases ----------

def test_preview_of_an_empty_list_is_a_clear_error(tab):
    with pytest.raises(ValueError, match="Nothing to merge"):
        tab.build_preview()


def test_preview_with_a_missing_file_names_it(tab, files, tmp_path):
    tab.add_files([files[0], str(tmp_path / "gone.pdf")])
    with pytest.raises(ValueError, match="File not found: .*gone.pdf"):
        tab.build_preview()


def test_preview_with_a_corrupt_file_names_it(tab, files, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("this is not a pdf")
    tab.add_files([files[0], str(bad)])
    with pytest.raises(ValueError, match="Could not read .*bad.pdf.*not a valid PDF"):
        tab.build_preview()


def test_errors_reach_the_user_through_run_safely(qapp, monkeypatch):
    shown = []
    monkeypatch.setattr(docu.QMessageBox, "critical", lambda *a: shown.append(a[2]))
    w = docu.MainWindow()
    w.run_safely(w.merge_tab.do_preview)
    assert shown == ["Nothing to merge"]


def test_merge_tab_lives_in_the_main_window(qapp):
    w = docu.MainWindow()
    assert w.merge_tab.window() is w and w.tabs.tabText(0) == "Merge"


# ---------- pdf_ops.merge corner cases ----------

def test_merge_to_a_stream_and_to_a_path_match(files, tmp_path):
    import io
    buf = io.BytesIO()
    pdf_ops.merge(files, buf)
    pdf_ops.merge(files, str(tmp_path / "p.pdf"))
    assert texts(io.BytesIO(buf.getvalue())) == texts(str(tmp_path / "p.pdf"))


def test_merge_same_file_twice_and_a_single_file(files, tmp_path):
    out = str(tmp_path / "m.pdf")
    pdf_ops.merge([files[0], files[0]], out)
    assert texts(out) == ["A1", "A2", "A1", "A2"]
    pdf_ops.merge([files[1]], out)
    assert texts(out) == ["B1", "B2"]


def test_failed_merge_leaves_no_output_file(files, tmp_path):
    out = tmp_path / "m.pdf"
    with pytest.raises(ValueError):
        pdf_ops.merge([files[0], str(tmp_path / "nope.pdf")], str(out))
    assert not out.exists()
