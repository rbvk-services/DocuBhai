"""DocuBhai - Windows 2003 style PDF toolbox (PySide6)."""
import ctypes
import io
import os
import sys

from pypdf import PdfReader
from PySide6.QtCore import Qt

from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

import listops
import pdf_ops
from viewer import ViewTab

ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
TITLE = "DocuBhai Aristocrat Reader"
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets").replace("\\", "/")

STYLE = """
* { font-family: 'Comic Sans MS'; font-size: 10pt; color: black; }
QMainWindow, QWidget { background: #ECE9D8; }
QTabWidget::pane { border: 2px outset #FFFFFF; }
QTabBar::tab { background: #F4F3EE; border: 1px solid #919B9C; padding: 4px 12px; }
QTabBar::tab:selected { background: #FFFFFF; border-top: 3px solid #FF9C00; }
QPushButton { background: #ECE9D8; border: 2px outset #FFFFFF; padding: 3px 10px; min-width: 70px; }
QPushButton:pressed { border: 2px inset #808080; }
QLineEdit, QListWidget, QTextEdit, QSpinBox, QComboBox { background: white; border: 2px inset #808080; }
QLabel#title { background: #0054E3; color: white; font-weight: bold; padding: 4px; }
QStatusBar { border-top: 1px solid #808080; }
QCheckBox::indicator, QListWidget::indicator { width: 16px; height: 16px; image: url(ASSETS/checkbox-off.png); }
QCheckBox::indicator:checked, QListWidget::indicator:checked { image: url(ASSETS/checkbox-on.png); }
QCheckBox::indicator:indeterminate { image: url(ASSETS/checkbox-partial.png); }
""".replace("ASSETS", ASSETS)


def pick_open(parent, multi=False):
    flt = "PDF files (*.pdf)"
    if multi:
        return QFileDialog.getOpenFileNames(parent, "Open PDFs", "", flt)[0]
    return QFileDialog.getOpenFileName(parent, "Open PDF", "", flt)[0]


class FileRow(QWidget):
    """A line edit + Browse button for choosing one PDF."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit = QLineEdit()
        btn = QPushButton("Browse...")
        btn.clicked.connect(lambda: self.edit.setText(pick_open(self) or self.edit.text()))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.edit)
        lay.addWidget(btn)

    def path(self):
        return self.edit.text().strip()


class PreviewDialog(QDialog):
    """Pop-up showing the real merged PDF, so it can be checked (and saved) before committing."""
    def __init__(self, data, n_files, n_pages, parent=None):
        super().__init__(parent)
        self.data = data
        self.setWindowTitle(f"Merge preview - {n_files} files, {n_pages} pages")
        self.resize(720, 560)
        self.view = ViewTab(with_open=False)
        self.view.load_bytes(data)
        save, close = QPushButton("Save merged PDF..."), QPushButton("Close")
        save.clicked.connect(lambda: self.save())
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(save)
        row.addWidget(close)
        lay = QVBoxLayout(self)
        lay.addWidget(self.view)
        lay.addLayout(row)

    def showEvent(self, e):
        super().showEvent(e)
        self.view.fit_width()

    def save(self, out=None):
        out = out or QFileDialog.getSaveFileName(self, "Save merged PDF", "merged.pdf", "PDF (*.pdf)")[0]
        if out:
            with open(out, "wb") as f:
                f.write(self.data)


class MergeTab(QWidget):
    """File list with a tick box at the right of each row. Clicking a row toggles its tick; Remove and the
    arrows act on the ticked rows. Preview / Merge always use every file in list order."""
    def __init__(self):
        super().__init__()
        self.list = QListWidget()
        self.list.setDragDropMode(QListWidget.InternalMove)  # drag to reorder
        self.list.setLayoutDirection(Qt.RightToLeft)  # puts the tick box on the right
        self.list.setTextElideMode(Qt.ElideMiddle)
        self.all = QCheckBox("Select all")
        self.count = QLabel()
        self.btn = {}
        for key, text, tip in (("add", "Add...", "Add PDFs"), ("rm", "Remove", "Remove ticked files"),
                               ("up", "▲", "Move up"), ("down", "▼", "Move down"),
                               ("clear", "Clear", "Remove all files"),
                               ("preview", "Preview...", "Preview the merged PDF"), ("go", "Merge...", "Merge and save")):
            self.btn[key] = b = QPushButton(text)
            b.setToolTip(tip)
        for key in ("up", "down"):
            self.btn[key].setMinimumWidth(0)
        self.btn["add"].clicked.connect(lambda: self.add_files(pick_open(self, True)))
        self.btn["rm"].clicked.connect(self.remove_checked)
        self.btn["up"].clicked.connect(lambda: self.move(-1))
        self.btn["down"].clicked.connect(lambda: self.move(1))
        self.btn["clear"].clicked.connect(self.clear)
        self.btn["preview"].clicked.connect(lambda: self.window().run_safely(self.do_preview))
        self.btn["go"].clicked.connect(lambda: self.window().run_safely(self.do_merge))
        self.all.clicked.connect(lambda on: self.write(listops.set_all(self.entries(), on)))
        self.list.itemClicked.connect(lambda it: self.write(listops.toggle(self.entries(), self.list.row(it))))
        m = self.list.model()  # drag-reorder changes the model directly
        for sig in (m.rowsMoved, m.rowsInserted, m.rowsRemoved):
            sig.connect(lambda *_: self.refresh())
        arrows = QHBoxLayout()
        arrows.addWidget(self.btn["up"])
        arrows.addWidget(self.btn["down"])
        side = QVBoxLayout()
        side.addWidget(self.btn["add"])
        side.addWidget(self.btn["rm"])
        side.addLayout(arrows)
        side.addWidget(self.btn["clear"])
        side.addStretch()
        side.addWidget(self.btn["preview"])
        side.addWidget(self.btn["go"])
        head = QHBoxLayout()
        head.addWidget(self.all)
        head.addStretch()
        head.addWidget(self.count)
        left = QVBoxLayout()
        left.addLayout(head)
        left.addWidget(self.list)
        lay = QHBoxLayout(self)
        lay.addLayout(left)
        lay.addLayout(side)
        self.refresh()

    def items(self):
        return [name for name, _ in self.entries()]

    def entries(self):
        """[(path, ticked)] in list order - the model the pure functions in listops work on."""
        rows = [self.list.item(i) for i in range(self.list.count())]
        return [(it.text(), it.data(Qt.CheckStateRole) == Qt.Checked) for it in rows]

    def write(self, entries):
        """Rebuild the list from [(path, ticked)]."""
        self.list.model().blockSignals(True)
        self.list.clear()
        for name, ticked in entries:
            it = QListWidgetItem(name)
            it.setData(Qt.CheckStateRole, Qt.Checked if ticked else Qt.Unchecked)  # drawn; toggled by row click
            it.setTextAlignment(Qt.AlignLeft | Qt.AlignAbsolute | Qt.AlignVCenter)
            self.list.addItem(it)
        self.list.model().blockSignals(False)
        self.refresh()

    def refresh(self):
        """Sync buttons, 'Select all' and row colours with the current list."""
        e = self.entries()
        state = listops.check_state(e)
        self.all.setTristate(False)
        self.all.setCheckState({"none": Qt.Unchecked, "some": Qt.PartiallyChecked, "all": Qt.Checked}[state])
        self.all.setEnabled(bool(e))
        self.btn["rm"].setEnabled(state != "none")
        self.btn["up"].setEnabled(listops.can_move(e, -1))
        self.btn["down"].setEnabled(listops.can_move(e, 1))
        self.btn["clear"].setEnabled(bool(e))
        self.count.setText(f"{sum(c for _, c in e)} of {len(e)} selected")
        for i, (_, ticked) in enumerate(e):
            it = self.list.item(i)
            it.setBackground(QColor("#316AC5") if ticked else QColor("white"))
            it.setForeground(QColor("white") if ticked else QColor("black"))

    def add_files(self, paths):
        self.write(self.entries() + [(p, False) for p in paths])

    def remove_checked(self):
        self.write(listops.remove_checked(self.entries()))

    def move(self, step):
        self.write(listops.move_checked(self.entries(), step))

    def clear(self):
        n = self.list.count()
        if n and QMessageBox.question(self, "DocuBhai", f"Remove all {n} files from the list?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.write([])

    def build_preview(self):
        """Merge every file in list order in memory -> (pdf bytes, page count)."""
        buf = io.BytesIO()
        pdf_ops.merge(self.items(), buf)
        return buf.getvalue(), len(PdfReader(buf).pages)

    def do_preview(self):
        data, pages = self.build_preview()
        PreviewDialog(data, self.list.count(), pages, self).exec()

    def do_merge(self, out=None):
        out = out or QFileDialog.getSaveFileName(self, "Save merged PDF", "merged.pdf", "PDF (*.pdf)")[0]
        if out:
            pdf_ops.merge(self.items(), out)
            return f"Merged {self.list.count()} files into {out}"


class SplitTab(QWidget):
    def __init__(self):
        super().__init__()
        self.src = FileRow()
        self.spec = QLineEdit()
        self.spec.setPlaceholderText("e.g. 1-3,5   (blank = every page)")
        go = QPushButton("Split...")
        go.clicked.connect(lambda: self.window().run_safely(self.do_split))
        lay = QFormLayout(self)
        lay.addRow("PDF:", self.src)
        lay.addRow("Pages:", self.spec)
        lay.addRow(go)

    def do_split(self, out_dir=None):
        out_dir = out_dir or QFileDialog.getExistingDirectory(self, "Output folder")
        if out_dir:
            files = pdf_ops.split(self.src.path(), out_dir, self.spec.text())
            return f"Created {len(files)} files in {out_dir}"


class SignTab(QWidget):
    def __init__(self):
        super().__init__()
        self.src = FileRow()
        self.text = QLineEdit()
        self.page = QSpinBox()
        self.page.setMinimum(1)
        self.position = QComboBox()
        self.position.addItems(pdf_ops.POSITIONS)
        go = QPushButton("Sign...")
        go.clicked.connect(lambda: self.window().run_safely(self.do_sign))
        lay = QFormLayout(self)
        lay.addRow("PDF:", self.src)
        lay.addRow("Signature:", self.text)
        lay.addRow("Page:", self.page)
        lay.addRow("Position:", self.position)
        lay.addRow(go)

    def do_sign(self, out=None):
        out = out or QFileDialog.getSaveFileName(self, "Save signed PDF", "signed.pdf", "PDF (*.pdf)")[0]
        if out:
            pdf_ops.sign(self.src.path(), out, self.text.text(), self.page.value(), self.position.currentText())
            return f"Signed PDF saved to {out}"


class CompareTab(QWidget):
    def __init__(self):
        super().__init__()
        self.a, self.b = FileRow(), FileRow()
        self.result = QTextEdit()
        self.result.setReadOnly(True)
        go = QPushButton("Compare")
        go.clicked.connect(lambda: self.window().run_safely(self.do_compare))
        lay = QFormLayout(self)
        lay.addRow("First PDF:", self.a)
        lay.addRow("Second PDF:", self.b)
        lay.addRow(go)
        lay.addRow(self.result)

    def do_compare(self):
        self.result.setPlainText(pdf_ops.compare(self.a.path(), self.b.path()))
        return "Comparison done"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setWindowIcon(QIcon(ICON))
        self.resize(760, 520)
        banner = QLabel("  " + TITLE)
        banner.setObjectName("title")
        self.tabs = QTabWidget()
        self.merge_tab, self.split_tab = MergeTab(), SplitTab()
        self.sign_tab, self.compare_tab = SignTab(), CompareTab()
        self.view_tab = ViewTab()
        for t, name in ((self.merge_tab, "Merge"), (self.split_tab, "Split"),
                        (self.sign_tab, "Sign"), (self.compare_tab, "Compare"),
                        (self.view_tab, "View")):
            self.tabs.addTab(t, name)
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(banner)
        lay.addWidget(self.tabs)
        self.setCentralWidget(box)
        self.statusBar().showMessage("Ready")

    def run_safely(self, fn, *args):
        """Single choke point: run an action, show result or error."""
        try:
            msg = fn(*args)
            if msg:
                self.statusBar().showMessage(msg)
                QMessageBox.information(self, "DocuBhai", msg)
        except Exception as e:
            self.statusBar().showMessage("Error")
            QMessageBox.critical(self, "DocuBhai - Error", str(e))


def main():
    if sys.platform == "win32":  # own taskbar identity so Windows shows our icon, not python's
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DocuBhai.AristocratReader")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON))
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
