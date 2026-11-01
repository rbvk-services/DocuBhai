"""GUI-free PDF operations: merge, split, sign, compare."""
import difflib
import io
import os

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def merge(paths, out):
    """Append all pages of `paths` (in the given order) into `out` (a path or a writable binary stream)."""
    if not paths:
        raise ValueError("Nothing to merge")
    w = PdfWriter()
    for p in paths:
        try:
            pages = PdfReader(p).pages
            for page in pages:
                w.add_page(page)
        except FileNotFoundError:
            raise ValueError(f"File not found: {p}")
        except Exception:
            raise ValueError(f"Could not read '{p}': not a valid PDF")
    if hasattr(out, "write"):
        w.write(out)
    else:
        with open(out, "wb") as f:
            w.write(f)
    return out


def parse_ranges(spec, n):
    """'1-3,5' -> [[0,1,2],[4]] (0-based page indexes). Empty spec = one range per page."""
    if not spec.strip():
        return [[i] for i in range(n)]
    ranges = []
    for part in spec.split(","):
        try:
            a, _, b = part.strip().partition("-")
            lo, hi = int(a), int(b or a)
        except ValueError:
            raise ValueError(f"Bad range: '{part.strip()}'")
        if not 1 <= lo <= hi <= n:
            raise ValueError(f"Range '{part.strip()}' outside 1-{n}")
        ranges.append(list(range(lo - 1, hi)))
    return ranges


def split(src, out_dir, spec=""):
    """Write one PDF per range into out_dir; return the file paths."""
    r = PdfReader(src)
    base = os.path.splitext(os.path.basename(src))[0]
    os.makedirs(out_dir, exist_ok=True)
    outs = []
    for i, pages in enumerate(parse_ranges(spec, len(r.pages)), 1):
        w = PdfWriter()
        for p in pages:
            w.add_page(r.pages[p])
        path = os.path.join(out_dir, f"{base}_part{i}.pdf")
        with open(path, "wb") as f:
            w.write(f)
        outs.append(path)
    return outs


POSITIONS = ("bottom-right", "bottom-left", "top-right", "top-left")


def sign(src, out, text, page=1, position="bottom-right"):
    """Stamp `text` as a signature on a page (1-based) at a corner."""
    r = PdfReader(src)
    if not text.strip():
        raise ValueError("Signature text is empty")
    if not 1 <= page <= len(r.pages):
        raise ValueError(f"Page must be 1-{len(r.pages)}")
    if position not in POSITIONS:
        raise ValueError(f"Position must be one of {POSITIONS}")
    target = r.pages[page - 1]
    pw, ph = float(target.mediabox.width), float(target.mediabox.height)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(pw, ph))
    c.setFont("Helvetica-Oblique", 18)
    tw = c.stringWidth(text, "Helvetica-Oblique", 18)
    x = pw - tw - 36 if "right" in position else 36
    y = 36 if "bottom" in position else ph - 54
    c.drawString(x, y, text)
    c.line(x, y - 3, x + tw, y - 3)
    c.save()
    buf.seek(0)
    target.merge_page(PdfReader(buf).pages[0])
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)
    with open(out, "wb") as f:
        w.write(f)
    return out


def compare(a, b):
    """Return a text diff of two PDFs, or 'The PDFs have identical text.'"""
    def lines(path):
        out = []
        for i, p in enumerate(PdfReader(path).pages, 1):
            out += [f"[p{i}] {l}" for l in (p.extract_text() or "").splitlines()]
        return out
    diff = list(difflib.unified_diff(lines(a), lines(b), os.path.basename(a),
                                     os.path.basename(b), lineterm=""))
    return "\n".join(diff) if diff else "The PDFs have identical text."
