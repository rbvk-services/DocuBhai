"""DocuBhai - Windows 2003 style PDF toolbox (PySide6)."""
import ctypes
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QSpinBox,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

import pdf_ops
from viewer import ViewTab

ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
TITLE = "DocuBhai Aristocrat Reader"

STYLE = """
* { font-family: 'Comic Sans MS'; font-size: 10pt; color: black; }
QMainWindow, QWidget { background: #ECE9D8; }
QTabWidget::pane { border: 2px outset #FFFFFF; }
QTabBar::tab { background: #F4F3EE; border: 1px solid #919B9C; padding: 4px 12px; }
QTabBar::tab:selected { background: #FFFFFF; border-top: 3px solid #FF9C00; }
QPushButton { background: #ECE9D8; border: 2px outset #FFFFFF; padding: 3px 10px; min-width: 70px; }
QPushButton:pressed { border: 2px inset #808080; }
QLineEdit, QListWidget, QTextEdit, QSpinBox, QComboBox { background: white; border: 2px inset #808080; }
QListWidget::item:selected { background: #316AC5; color: white; }
QLabel#title { background: #0054E3; color: white; font-weight: bold; padding: 4px; }
QStatusBar { border-top: 1px solid #808080; }
"""


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


class MergeTab(QWidget):
    def __init__(self):
        super().__init__()
        self.list = QListWidget()
        self.list.setDragDropMode(QListWidget.InternalMove)  # drag to reorder
        add, rm = QPushButton("Add..."), QPushButton("Remove")
        up, down = QPushButton("Move Up"), QPushButton("Move Down")
        go = QPushButton("Merge...")
        add.clicked.connect(lambda: self.list.addItems(pick_open(self, True)))
        rm.clicked.connect(lambda: [self.list.takeItem(self.list.row(i)) for i in self.list.selectedItems()])
        up.clicked.connect(lambda: self.move(-1))
        down.clicked.connect(lambda: self.move(1))
        go.clicked.connect(lambda: self.window().run_safely(self.do_merge))
        side = QVBoxLayout()
        for b in (add, rm, up, down):
            side.addWidget(b)
        side.addStretch()
        side.addWidget(go)
        lay = QHBoxLayout(self)
        lay.addWidget(self.list)
        lay.addLayout(side)

    def items(self):
        return [self.list.item(i).text() for i in range(self.list.count())]

    def move(self, d):
        r = self.list.currentRow()
        if 0 <= r + d < self.list.count():
            self.list.insertItem(r + d, self.list.takeItem(r))
            self.list.setCurrentRow(r + d)

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
