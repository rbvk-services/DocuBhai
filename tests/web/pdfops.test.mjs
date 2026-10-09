import assert from "node:assert/strict";
import { test } from "node:test";
import { PDFDocument, StandardFonts } from "../../web/vendor/pdf-lib.esm.min.js";
import * as ops from "../../web/js/pdfops.js";
import * as pdfjs from "../../web/vendor/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("../../web/vendor/pdf.worker.min.mjs", import.meta.url).href;

async function makePdf(texts) {
  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.Helvetica);
  for (const t of texts) doc.addPage([595, 842]).drawText(t, { x: 100, y: 700, size: 14, font });
  return doc.save();
}
const pageCount = async (bytes) => (await PDFDocument.load(bytes)).getPageCount();
const lines = async (bytes) => (await ops.extractLines(pdfjs, bytes.buffer ?? bytes)).flat();

test("merge respects order", async () => {
  const a = await makePdf(["A1", "A2"]), b = await makePdf(["B1"]);
  const out = await ops.merge([b, a]);
  assert.deepEqual(await lines(out), ["B1", "A1", "A2"]);
});

test("merge with nothing throws", async () => {
  await assert.rejects(ops.merge([]), /Nothing to merge/);
});

test("split by ranges and every page", async () => {
  const src = await makePdf(["P1", "P2", "P3", "P4"]);
  const parts = await ops.split(src, "1-2,4");
  assert.deepEqual(await Promise.all(parts.map(pageCount)), [2, 1]);
  assert.deepEqual(await lines(parts[1]), ["P4"]);
  assert.equal((await ops.split(src, "")).length, 4);
});

for (const spec of ["0-1", "3-9", "abc", "2-1"])
  test(`split rejects bad range '${spec}'`, async () => {
    await assert.rejects(ops.split(await makePdf(["P1", "P2", "P3"]), spec), /range|Range/i);
  });

test("sign stamps text on the chosen page only", async () => {
  const src = await makePdf(["P1", "P2"]);
  const out = await ops.sign(src, "Rohak", 2);
  assert.equal(await pageCount(out), 2);
  const pages = await ops.extractLines(pdfjs, out.buffer);
  assert.ok(pages[1].includes("Rohak") && !pages[0].includes("Rohak"));
});

test("sign validates input", async () => {
  const src = await makePdf(["P1"]);
  await assert.rejects(ops.sign(src, "  "), /empty/);
  await assert.rejects(ops.sign(src, "me", 5), /Page must be/);
  await assert.rejects(ops.sign(src, "me", 1, "middle"), /Position/);
});

test("compare reports identical and different text", async () => {
  const a = await ops.extractLines(pdfjs, (await makePdf(["Hello", "World"])).buffer);
  const b = await ops.extractLines(pdfjs, (await makePdf(["Hello", "World"])).buffer);
  const c = await ops.extractLines(pdfjs, (await makePdf(["Hello", "Mars"])).buffer);
  assert.match(ops.compare(a, b), /identical/);
  const diff = ops.compare(a, c);
  assert.ok(diff.includes("-[p2] World") && diff.includes("+[p2] Mars"));
});

test("diffLines handles insertions, deletions and empty inputs", () => {
  const d = ops.diffLines(["a", "b", "c"], ["a", "x", "c", "d"]);
  assert.deepEqual(d.map((x) => x.op + x.line), [" a", "-b", "+x", " c", "+d"]);
  assert.deepEqual(ops.diffLines([], []), []);
});
