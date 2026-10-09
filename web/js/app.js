// UI glue: tabs, merge list, split/sign/compare forms, viewer toolbar. All work happens in the browser.
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
const mergeFiles = []; // [{file}] in list order
let selected = -1;

function renderMerge() {
  const ul = $("merge-list");
  ul.replaceChildren(...mergeFiles.map((f, i) => {
    const li = document.createElement("li");
    li.textContent = f.name;
    li.draggable = true;
    li.className = i === selected ? "selected" : "";
    li.onclick = () => { selected = i; renderMerge(); };
    li.ondragstart = (e) => e.dataTransfer.setData("text/x-index", String(i));
    li.ondragover = (e) => { e.preventDefault(); li.classList.add("over"); };
    li.ondragleave = () => li.classList.remove("over");
    li.ondrop = (e) => {
      e.preventDefault();
      e.stopPropagation();
      const from = e.dataTransfer.getData("text/x-index");
      if (from !== "") move(+from, i);
      else addFiles(e.dataTransfer.files);
    };
    return li;
  }));
}

function move(from, to) {
  mergeFiles.splice(to, 0, ...mergeFiles.splice(from, 1));
  selected = to;
  renderMerge();
}

function addFiles(files) {
  mergeFiles.push(...[...files].filter((f) => /\.pdf$/i.test(f.name) || f.type === "application/pdf"));
  renderMerge();
}

$("merge-add").onchange = (e) => { addFiles(e.target.files); e.target.value = ""; };
$("merge-list").ondragover = (e) => e.preventDefault();
$("merge-list").ondrop = (e) => { e.preventDefault(); addFiles(e.dataTransfer.files); };
$("merge-remove").onclick = () => { if (selected >= 0) { mergeFiles.splice(selected, 1); selected = -1; renderMerge(); } };
$("merge-up").onclick = () => selected > 0 && move(selected, selected - 1);
$("merge-down").onclick = () => selected >= 0 && selected < mergeFiles.length - 1 && move(selected, selected + 1);
$("merge-go").onclick = safely(async () => {
  const bytes = await ops.merge(await Promise.all(mergeFiles.map(readFile)));
  download(bytes, "merged.pdf");
  return `Merged ${mergeFiles.length} files into merged.pdf`;
});

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
