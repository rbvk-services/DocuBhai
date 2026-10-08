import os
import sys

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pdf_ops  # noqa: E402


def make_pdf(path, texts):
    c = canvas.Canvas(str(path))
    for t in texts:
        c.drawString(100, 700, t)
        c.showPage()
    c.save()
    return str(path)


def page_text(path, i):
    return PdfReader(path).pages[i].extract_text()


def test_merge_respects_order(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", ["A1", "A2"])
    b = make_pdf(tmp_path / "b.pdf", ["B1"])
    out = pdf_ops.merge([b, a], str(tmp_path / "m.pdf"))
    r = PdfReader(out)
    assert [p.extract_text().strip() for p in r.pages] == ["B1", "A1", "A2"]


def test_merge_empty_raises(tmp_path):
    with pytest.raises(ValueError):
        pdf_ops.merge([], str(tmp_path / "m.pdf"))


def test_split_ranges(tmp_path):
    src = make_pdf(tmp_path / "s.pdf", ["P1", "P2", "P3", "P4"])
    outs = pdf_ops.split(src, str(tmp_path / "o"), "1-2,4")
    assert [len(PdfReader(o).pages) for o in outs] == [2, 1]
    assert page_text(outs[1], 0).strip() == "P4"


def test_split_every_page(tmp_path):
    src = make_pdf(tmp_path / "s.pdf", ["P1", "P2", "P3"])
    assert len(pdf_ops.split(src, str(tmp_path / "o"))) == 3


@pytest.mark.parametrize("spec", ["0-1", "3-9", "abc", "2-1"])
def test_split_bad_range(tmp_path, spec):
    src = make_pdf(tmp_path / "s.pdf", ["P1", "P2", "P3"])
    with pytest.raises(ValueError):
        pdf_ops.split(src, str(tmp_path / "o"), spec)


def test_sign_adds_text_and_keeps_pages(tmp_path):
    src = make_pdf(tmp_path / "s.pdf", ["P1", "P2"])
    out = pdf_ops.sign(src, str(tmp_path / "x.pdf"), "Rohak", page=2)
    assert len(PdfReader(out).pages) == 2
    assert "Rohak" in page_text(out, 1)
    assert "Rohak" not in page_text(out, 0)


def test_sign_validation(tmp_path):
    src = make_pdf(tmp_path / "s.pdf", ["P1"])
    with pytest.raises(ValueError):
        pdf_ops.sign(src, str(tmp_path / "x.pdf"), "  ")
    with pytest.raises(ValueError):
        pdf_ops.sign(src, str(tmp_path / "x.pdf"), "me", page=5)


def test_compare_identical_and_different(tmp_path):
    a = make_pdf(tmp_path / "a.pdf", ["Hello", "World"])
    b = make_pdf(tmp_path / "b.pdf", ["Hello", "World"])
    c = make_pdf(tmp_path / "c.pdf", ["Hello", "Mars"])
    assert "identical" in pdf_ops.compare(a, b)
    diff = pdf_ops.compare(a, c)
    assert "-[p2] World" in diff and "+[p2] Mars" in diff
