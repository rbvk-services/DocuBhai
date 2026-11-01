# DocuBhai – Architecture

A tiny Windows-2003-style desktop app for PDF chores: **merge, split, sign, compare, view**.

## Components

| File | Role | Depends on |
|---|---|---|
| `pdf_ops.py` | Pure logic. No GUI imports. Four functions: `merge`, `split`, `sign`, `compare`. `merge` writes to a path or an in-memory stream and names the bad file in its errors. | `pypdf`, `reportlab` |
| `listops.py` | Pure rules for the Merge list: tick/untick, select-all state, move the ticked group, remove. Works on `(name, ticked)` tuples; no Qt. | - |
| `viewer.py` | `ViewTab` (toolbar + scroll area) and `PageView` (draws one rendered page plus the selection highlight). | `PySide6.QtPdf` |
| `app.py` | Qt GUI. Main window with one tab per feature; each tab collects inputs and calls `pdf_ops`. | `PySide6`, `pdf_ops` |
| `tests/test_pdf_ops.py` | Unit tests for each feature, using generated PDFs. | `pdf_ops` |
| `tests/test_app.py` | Sanity tests: window builds, tabs exist, a merge is driven through the GUI. | `app` |

## Layers

```
 ┌────────────────────────────────────────────┐
 │ app.py  (presentation)                     │
 │  MainWindow ── QTabWidget                  │
 │   ├─ MergeTab    (reorderable list)        │
 │   ├─ SplitTab    (page ranges)             │
 │   ├─ SignTab     (text signature, position)│
 │   ├─ CompareTab  (text diff report)        │
 │   └─ ViewTab     (viewer.py, uses QtPdf)   │
 └───────────────┬────────────────────────────┘
                 │ plain function calls (paths in, paths/strings out)
 ┌───────────────▼────────────────────────────┐
 │ pdf_ops.py  (logic, GUI-free, testable)    │
 └───────────────┬────────────────────────────┘
                 │
          pypdf (read/write/merge)  reportlab (draw signature overlay)
```

## Data flow per feature

1. **Merge** – user adds PDFs to a list; each row has a tick box on the right (clicking a row toggles it, *Select all* sits above). **Remove** and the **▲/▼** arrows act on the ticked rows (the ticked group moves one step, jumping over its neighbour, and the arrows grey out when nothing can move); rows can also be dragged. **Clear** asks first. **Preview** merges in memory (`merge(paths, BytesIO)`) and opens the real result in a pop-up viewer with *Save*; **Merge** writes the file. Preview and Merge always use *every* file in list order - ticks only drive Remove and the arrows. `MergeTab` keeps the Qt list as the view and calls `listops` on `entries()`, then `write()`s the result back.
2. **Split** – user picks a PDF and a range spec (`"1-3,5"`) or "every page" → `split(src, out_dir, ranges)` writes one PDF per range; returns the paths.
3. **Sign** – user picks a PDF, types a signature, chooses page + corner → `sign(src, out, text, page, position)` renders the text with reportlab onto a one-page overlay and merges it onto the target page.
4. **Compare** – user picks two PDFs → `compare(a, b)` extracts text per page and returns a unified-diff style report (or "identical"), shown in a read-only text box.
5. **View** – `ViewTab.load` opens the file in a `QPdfDocument`. `PageView` lays out *all* pages in one tall widget inside a `QScrollArea` (continuous scroll) using only page sizes, and renders a page lazily when it enters the paint region. Rendered pages are composited onto opaque white, drawn at >=2x the screen resolution and smoothly downscaled, and kept in a small LRU cache (8 pages, pixel-capped at high zoom). Scrolling updates the current-page box; Prev/Next/page box scroll to a page top; `-`/`+`/Fit Width/Ctrl+wheel re-layout at a new `scale` (px per PDF point; 1.333 = 100%) while keeping the same spot in view. Dragging the mouse calls `QPdfDocument.getSelection(page, start, end)` (selection stays within the page where the drag began); the polygons are painted as a highlight and the text is copied by Copy / Ctrl+C. The viewer does not use `pdf_ops`.

## Error handling

`pdf_ops` raises `ValueError` for bad input (empty list, bad range, page out of bounds). The GUI catches `Exception` at one choke point (`run_safely`) and shows a `QMessageBox` – logic never touches widgets.

## Look & feel

A global Qt stylesheet gives Windows 2003 ("Luna"/classic): `#ECE9D8` beige surfaces, raised-bevel buttons, blue `#0054E3` title/selection, and **Comic Sans MS** in black everywhere (white only on the blue banner and selected list rows). The Fusion style is used as a base for consistent rendering.

## Testing strategy

- `pdf_ops` tests build small PDFs with reportlab (each page stamped with unique text), run an operation, and verify with pypdf (page counts, order, text).
- `tests/test_viewer.py` loads a generated PDF, checks white page background, render resolution, continuous scroll/current page, cache bound, page clamping, zoom limits, fit-width, and simulates a mouse drag to verify select + copy.
- `tests/test_listops.py` and `tests/web/mergelist.test.mjs` test the list rules table-driven, plus an exhaustive check of every tick pattern on 0-5 items (`can_move` must agree with `move`; nothing lost, duplicated or re-ordered).
- `tests/test_mergetab.py` drives the desktop Merge tab: ticks, select-all, arrows at the edges, drag-reorder, Clear (declined / confirmed / empty), preview content and order, and negative cases (empty list, missing file, corrupt file, cancelled save).
- GUI tests run with `QT_QPA_PLATFORM=offscreen`, no user interaction needed.

## Web version (`web/`, deployed to GitHub Pages)

A static, client-side port of the same five features – GitHub Pages cannot run Python/Qt, so the logic is rewritten in
JavaScript and everything runs in the visitor's browser (nothing is uploaded).

| File | Role |
|---|---|
| `web/index.html`, `web/style.css` | One page, five tab panels, Windows 2003 look (Comic Sans, black text, Luna title bar). Relative paths only, so it works at `/` and under `/DocuBhai/`. |
| `web/js/pdfops.js` | Port of `pdf_ops.py`: `merge`, `split`, `sign`, `compare` (+ `diffLines`, `extractLines`). Pure functions; uses **pdf-lib** for editing. |
| `web/js/mergelist.js` | Web twin of `listops.py` (+ `reorder` for drag-and-drop, `isPdf`, `summary`). Pure functions, unit-tested in Node. |
| `web/js/viewer.js` | `PdfViewer`: continuous scroll on **pdf.js** – all pages laid out as sized placeholders, rendered lazily by an `IntersectionObserver`, supersampled (>=2x) canvases on opaque white, a pdf.js text layer for selection/copy, zoom and fit-width. |
| `web/js/app.js` | UI glue; every action goes through `safely()` (the web twin of `run_safely`) which shows a dialog on error. |
| `web/vendor/` | pdf-lib, pdf.js (legacy build, worker, standard fonts, viewer CSS) and their licences – no CDN. |
| `scripts/serve.mjs` | Local static server (also used by the tests to mount the site under `/DocuBhai/`). |
| `.github/workflows/pages.yml` | CI: `npm test`, then publish `web/` to GitHub Pages. |

```
 browser ── index.html ── app.js ─┬─ pdfops.js ── pdf-lib   (merge / split / sign, bytes in -> bytes out)
                                  │            └─ pdf.js     (text extraction for compare)
                                  └─ viewer.js ── pdf.js     (render pages + text layer)
```

Tests: `tests/web/pdfops.test.mjs` (Node: each operation) and `tests/web/smoke.test.mjs` (headless Chrome/Edge drives the
real page: white page canvas, hi-res rendering, text selection, zoom, continuous scroll, the whole Merge tab - ticks on the
right, select-all, multi-select, arrows, remove, clear with confirmation, the merge preview pop-up, non-PDF and corrupt
files - compare, and the error dialog). See `DEPLOY.md` for hosting steps.
