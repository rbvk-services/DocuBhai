// Browser-side PDF operations (port of pdf_ops.py). Pure functions: bytes in, bytes/text out.
import { PDFDocument, StandardFonts, rgb } from "../vendor/pdf-lib.esm.min.js";

export const POSITIONS = ["bottom-right", "bottom-left", "top-right", "top-left"];

export async function merge(buffers) {
  if (!buffers.length) throw new Error("Nothing to merge");
  const out = await PDFDocument.create();
  for (const buf of buffers) {
    const src = await PDFDocument.load(buf);
    (await out.copyPages(src, src.getPageIndices())).forEach((p) => out.addPage(p));
  }
  return out.save();
}

/** '1-3,5' -> [[0,1,2],[4]] (0-based). Empty spec = one range per page. */
export function parseRanges(spec, n) {
  if (!spec.trim()) return Array.from({ length: n }, (_, i) => [i]);
  return spec.split(",").map((raw) => {
    const part = raw.trim();
    const m = /^(\d+)(?:-(\d+))?$/.exec(part);
    if (!m) throw new Error(`Bad range: '${part}'`);
    const lo = +m[1], hi = +(m[2] ?? m[1]);
    if (!(lo >= 1 && lo <= hi && hi <= n)) throw new Error(`Range '${part}' outside 1-${n}`);
    return Array.from({ length: hi - lo + 1 }, (_, i) => lo - 1 + i);
  });
}

export async function split(buffer, spec = "") {
  const src = await PDFDocument.load(buffer);
  const outs = [];
  for (const pages of parseRanges(spec, src.getPageCount())) {
    const doc = await PDFDocument.create();
    (await doc.copyPages(src, pages)).forEach((p) => doc.addPage(p));
    outs.push(await doc.save());
  }
  return outs;
}

/** Stamp `text` as a signature on a page (1-based) at a corner. */
export async function sign(buffer, text, page = 1, position = "bottom-right") {
  const doc = await PDFDocument.load(buffer);
  if (!text.trim()) throw new Error("Signature text is empty");
  if (!(page >= 1 && page <= doc.getPageCount())) throw new Error(`Page must be 1-${doc.getPageCount()}`);
  if (!POSITIONS.includes(position)) throw new Error(`Position must be one of ${POSITIONS.join(", ")}`);
  const target = doc.getPage(page - 1);
  const { width, height } = target.getSize();
  const font = await doc.embedFont(StandardFonts.HelveticaOblique);
  const tw = font.widthOfTextAtSize(text, 18);
  const x = position.includes("right") ? width - tw - 36 : 36;
  const y = position.includes("bottom") ? 36 : height - 54;
  target.drawText(text, { x, y, size: 18, font, color: rgb(0, 0, 0) });
  target.drawLine({ start: { x, y: y - 3 }, end: { x: x + tw, y: y - 3 }, thickness: 1, color: rgb(0, 0, 0) });
  return doc.save();
}

/** Line diff via LCS (common head/tail trimmed first). Returns [{op: ' '|'-'|'+', line}]. */
export function diffLines(a, b) {
  let s = 0;
  while (s < a.length && s < b.length && a[s] === b[s]) s++;
  let ea = a.length, eb = b.length;
  while (ea > s && eb > s && a[ea - 1] === b[eb - 1]) { ea--; eb--; }
  const A = a.slice(s, ea), B = b.slice(s, eb), n = A.length, m = B.length;
  if (n * m > 25e6) throw new Error("These PDFs differ too much to compare line by line");
  const t = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      t[i][j] = A[i] === B[j] ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
  const out = a.slice(0, s).map((line) => ({ op: " ", line }));
  let i = 0, j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && A[i] === B[j]) { out.push({ op: " ", line: A[i++] }); j++; }
    else if (j >= m || (i < n && t[i + 1][j] >= t[i][j + 1])) out.push({ op: "-", line: A[i++] });
    else out.push({ op: "+", line: B[j++] });
  }
  return out.concat(a.slice(ea).map((line) => ({ op: " ", line })));
}

/** pagesA/pagesB: arrays (per page) of text lines. Returns a diff report or the 'identical' message. */
export function compare(pagesA, pagesB, nameA = "first.pdf", nameB = "second.pdf") {
  const flat = (pages) => pages.flatMap((lines, i) => lines.map((l) => `[p${i + 1}] ${l}`));
  const changes = diffLines(flat(pagesA), flat(pagesB)).filter((d) => d.op !== " ");
  if (!changes.length) return "The PDFs have identical text.";
  return [`--- ${nameA}`, `+++ ${nameB}`, ...changes.map((d) => d.op + d.line)].join("\n");
}

/** Per-page text lines using a pdf.js module instance (kept injectable so tests can pass their own). */
export async function extractLines(pdfjs, buffer) {
  const task = pdfjs.getDocument({ data: new Uint8Array(buffer.slice(0)), verbosity: 0 });
  const doc = await task.promise;
  const pages = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const { items } = await (await doc.getPage(i)).getTextContent();
    const lines = [];
    let cur = "";
    for (const it of items) {
      cur += it.str;
      if (it.hasEOL) { lines.push(cur); cur = ""; }
    }
    if (cur) lines.push(cur);
    pages.push(lines.map((l) => l.trim()).filter(Boolean));
  }
  await task.destroy();
  return pages;
}
