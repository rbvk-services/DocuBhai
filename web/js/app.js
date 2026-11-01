// UI glue: tabs, merge list, split/sign/compare forms, viewer toolbar. All work happens in the browser.
import * as ml from "./mergelist.js";
import * as ops from "./pdfops.js";
import { PdfViewer, pdfjs } from "./viewer.js";

const $ = (id) => document.getElementById(id);
const readFile = (file) => file.arrayBuffer();

function say(text) { $("status").textContent = text; }

function dialog(title, text) {
  $("msg-title").textContent = title;
  $("msg-text").textContent = text;
  if ($("msg").showModal) $("msg").showModal();
  else alert(`${title}\n${text}`);
}

/** Single choke point: run an action, show its result message or its error. */
function safely(fn) {
  return async (...args) => {
    try {
      const msg = await fn(...args);
      if (msg) { say(msg); dialog("DocuBhai", msg); }
    } catch (err) {
      say("Error");
      dialog("DocuBhai - Error", err.message || String(err));
    }
  };
}

function download(bytes, name) {
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  return url;
}

const need = (file, what = "a PDF") => { if (!file) throw new Error(`Please choose ${what} first.`); return file; };
const baseName = (f) => f.name.replace(/\.pdf$/i, "");

// ---- tabs ----
document.querySelectorAll(".tabs button").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((t) => t.setAttribute("aria-selected", t === tab));
    document.querySelectorAll(".panel").forEach((p) => (p.hidden = p.id !== tab.dataset.tab));
  }));

// ---- merge ----
let list = []; // [{file, name, checked}] in list order; all the rules live in mergelist.js (unit-tested)

const dlg = (id) => $(id);

/** Yes/No pop-up (never the blocking window.confirm unless <dialog> is unsupported). */
function ask(title, text) {
  const d = dlg("confirm");
  if (!d.showModal) return Promise.resolve(confirm(`${title}\n${text}`));
  $("confirm-title").textContent = title;
  $("confirm-text").textContent = text;
  d.returnValue = "";
  return new Promise((resolve) => {
    d.addEventListener("close", () => resolve(d.returnValue === "yes"), { once: true });
    d.showModal();
  });
}

function setList(next) {
  list = next;
  renderMerge();
}

function renderMerge() {
  $("merge-list").replaceChildren(...list.map((it, i) => {
    const li = document.createElement("li");
    li.className = it.checked ? "selected" : "";
    li.draggable = true;
    const name = Object.assign(document.createElement("span"), { className: "name", textContent: it.name, title: it.name });
    const box = Object.assign(document.createElement("input"), { type: "checkbox", checked: it.checked });
    box.setAttribute("aria-label", `Select ${it.name}`);
    box.onchange = () => setList(ml.toggle(list, i));
    li.append(name, box);
    li.onclick = (e) => { if (e.target !== box) setList(ml.toggle(list, i)); }; // a click anywhere on the row ticks it
    li.ondragstart = (e) => e.dataTransfer.setData("text/x-index", String(i));
    li.ondragover = (e) => { e.preventDefault(); li.classList.add("over"); };
    li.ondragleave = () => li.classList.remove("over");
    li.ondrop = (e) => {
      e.preventDefault();
      e.stopPropagation();
      const from = e.dataTransfer.getData("text/x-index");
      if (from !== "") setList(ml.reorder(list, +from, i));
      else addFiles(e.dataTransfer.files);
    };
    return li;
  }));
  const state = ml.checkState(list);
  const all = $("merge-all");
  all.checked = state === "all";
  all.indeterminate = state === "some";
  all.disabled = !list.length;
  $("merge-remove").disabled = state === "none";
  $("merge-up").disabled = !ml.canMove(list, -1);
  $("merge-down").disabled = !ml.canMove(list, 1);
  $("merge-clear").disabled = !list.length;
  $("merge-count").textContent = ml.summary(list);
}

function addFiles(files) {
  const all = [...files], pdfs = all.filter(ml.isPdf);
  setList([...list, ...pdfs.map((file) => ({ file, name: file.name, checked: false }))]);
  if (pdfs.length < all.length) say(`Skipped ${all.length - pdfs.length} file(s) that are not PDFs`);
}

async function readAll() {
  return Promise.all(list.map(async (it) => {
    try { return await readFile(it.file); } catch { throw new Error(`Could not read '${it.name}' (was it moved or deleted?)`); }
  }));
}
const mergeNow = async () => ops.merge(await readAll(), list.map((it) => it.name));

$("merge-add").onchange = (e) => { addFiles(e.target.files); e.target.value = ""; };
$("merge-list").ondragover = (e) => e.preventDefault();
$("merge-list").ondrop = (e) => { e.preventDefault(); addFiles(e.dataTransfer.files); };
$("merge-all").onchange = (e) => setList(ml.setAll(list, e.target.checked));
$("merge-remove").onclick = () => setList(ml.removeChecked(list));
$("merge-up").onclick = () => setList(ml.moveChecked(list, -1));
$("merge-down").onclick = () => setList(ml.moveChecked(list, 1));
$("merge-clear").onclick = async () => {
  if (list.length && (await ask("Clear list", `Remove all ${list.length} files from the list?`))) setList([]);
};
$("merge-go").onclick = safely(async () => {
  download(await mergeNow(), "merged.pdf");
  return `Merged ${list.length} files into merged.pdf`;
});

// merge preview: build the real merged PDF in memory and show it in a pop-up before downloading
const preview = new PdfViewer($("preview-viewer"), {
  onPage: (i) => ($("pv-page").textContent = `Page ${i + 1} of ${preview.count}`),
  onZoom: (pct) => ($("pv-zoom").textContent = `${pct}%`),
});
let previewBytes = null;
$("merge-preview").onclick = safely(async () => {
  previewBytes = await mergeNow(); // errors (empty list, bad file) surface before the pop-up opens
  dlg("preview").showModal();
  await preview.load(previewBytes.buffer);
  $("preview-title").textContent = `Merge preview - ${list.length} files, ${preview.count} pages`;
  $("pv-page").textContent = `Page 1 of ${preview.count}`;
  preview.fitWidth();
});
$("pv-out").onclick = () => preview.zoomBy(0.8);
$("pv-in").onclick = () => preview.zoomBy(1.25);
$("pv-fit").onclick = () => preview.fitWidth();
$("preview-save").onclick = () => previewBytes && download(previewBytes, "merged.pdf");
dlg("preview").addEventListener("close", () => { preview.clear(); previewBytes = null; }); // free the pages

renderMerge();

// ---- split ----
$("split-go").onclick = safely(async () => {
  const file = need($("split-file").files[0]);
  const parts = await ops.split(await readFile(file), $("split-spec").value);
  $("split-out").replaceChildren(...parts.map((bytes, i) => {
    const name = `${baseName(file)}_part${i + 1}.pdf`;
    const a = Object.assign(document.createElement("a"), { textContent: `Download ${name}`, href: "#" });
    a.onclick = (e) => { e.preventDefault(); download(bytes, name); };
    const li = document.createElement("li");
    li.append(a);
    return li;
  }));
  return `Created ${parts.length} files - use the links below to download them`;
});

// ---- sign ----
$("sign-go").onclick = safely(async () => {
  const file = need($("sign-file").files[0]);
  const bytes = await ops.sign(await readFile(file), $("sign-text").value, +$("sign-page").value, $("sign-pos").value);
  download(bytes, `${baseName(file)}_signed.pdf`);
  return `Signed PDF saved as ${baseName(file)}_signed.pdf`;
});

// ---- compare ----
$("cmp-go").onclick = safely(async () => {
  const a = need($("cmp-a").files[0], "the first PDF"), b = need($("cmp-b").files[0], "the second PDF");
  const [la, lb] = await Promise.all([a, b].map(async (f) => ops.extractLines(pdfjs, await readFile(f))));
  $("cmp-out").textContent = ops.compare(la, lb, a.name, b.name);
  return "Comparison done";
});

// ---- view ----
const pageBox = $("view-page");
const viewer = new PdfViewer($("viewer"), {
  onPage: (i) => (pageBox.value = i + 1),
  onZoom: (pct) => ($("zoom-label").textContent = `${pct}%`),
});
$("view-file").onchange = safely(async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    await viewer.load(await readFile(file));
  } catch {
    throw new Error(`Could not open ${file.name}`);
  }
  pageBox.max = viewer.count;
  $("view-of").textContent = `of ${viewer.count}`;
  say(`Opened ${file.name}`);
});
$("view-prev").onclick = () => viewer.goTo(viewer.page - 1);
$("view-next").onclick = () => viewer.goTo(viewer.page + 1);
pageBox.onchange = () => viewer.goTo(+pageBox.value - 1);
$("zoom-out").onclick = () => viewer.zoomBy(0.8);
$("zoom-in").onclick = () => viewer.zoomBy(1.25);
$("view-fit").onclick = () => viewer.fitWidth();
$("view-copy").onclick = async () => say((await viewer.copySelection()) ? "Copied" : "Select some text first");

window.docubhai = { viewer, ops }; // handy for the smoke test / debugging
