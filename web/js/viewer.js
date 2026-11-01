// Continuous-scroll PDF viewer on pdf.js: lazy rendering, supersampled canvases, selectable text layer.
import * as pdfjs from "../vendor/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("../vendor/pdf.worker.min.mjs", import.meta.url).href;

export { pdfjs };
const FONTS = new URL("../vendor/standard_fonts/", import.meta.url).href;
const CSS_PX = 96 / 72;   // CSS px per PDF point at 100% zoom
const MARGIN = 10;        // px around / between pages
const MAX_PIXELS = 16e6;  // cap per rendered canvas so huge zooms stay safe

export class PdfViewer {
  constructor(container, { onPage = () => {}, onZoom = () => {} } = {}) {
    this.box = container;
    this.onPage = onPage;
    this.onZoom = onZoom;
    this.scale = CSS_PX;
    this.pages = []; // {el, pdfPage, size:[w,h] in points, token}
    this.page = 0;
    container.addEventListener("scroll", () => this.#trackPage(), { passive: true });
    container.addEventListener("wheel", (e) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      this.zoomBy(e.deltaY < 0 ? 1.25 : 0.8);
    }, { passive: false });
  }

  /** Drop the document and every rendered page (frees memory, e.g. when a pop-up closes). */
  clear() { this.#clear(); }

  get count() { return this.pages.length; }
  get zoomPercent() { return Math.round((this.scale / CSS_PX) * 100); }

  async load(buffer) {
    this.#clear();
    this.task = pdfjs.getDocument({ data: new Uint8Array(buffer.slice(0)), standardFontDataUrl: FONTS });
    this.doc = await this.task.promise;
    const pdfPages = await Promise.all(Array.from({ length: this.doc.numPages }, (_, i) => this.doc.getPage(i + 1)));
    this.pages = pdfPages.map((pdfPage) => {
      const [x0, y0, x1, y1] = pdfPage.view;
      const rot = pdfPage.rotate % 180 !== 0;
      const size = rot ? [y1 - y0, x1 - x0] : [x1 - x0, y1 - y0];
      const el = document.createElement("div");
      el.className = "page";
      this.box.appendChild(el);
      return { el, pdfPage, size, token: 0 };
    });
    this.#layout();
    this.goTo(0);
  }

  #clear() {
    this.observer?.disconnect();
    this.task?.destroy();
    this.box.replaceChildren();
    this.pages = [];
  }

  #layout() {
    for (const p of this.pages) {
      p.el.style.width = `${p.size[0] * this.scale}px`;
      p.el.style.height = `${p.size[1] * this.scale}px`;
      p.el.style.setProperty("--total-scale-factor", this.scale);
      this.#unrender(p);
    }
    this.observer?.disconnect();
    // render pages near the viewport, free the ones that scroll far away
    this.observer = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const p = this.pages.find((q) => q.el === e.target);
        e.isIntersecting ? this.#render(p) : this.#unrender(p);
      }
    }, { root: this.box, rootMargin: "1200px 0px" });
    this.pages.forEach((p) => this.observer.observe(p.el));
  }

  #unrender(p) {
    p.token++;
    p.task?.cancel();
    p.el.replaceChildren();
  }

  async #render(p) {
    if (p.el.firstChild) return;
    const token = ++p.token;
    const vp = p.pdfPage.getViewport({ scale: this.scale });
    // supersample (>= 2x) for crisp text, within a pixel budget
    let q = Math.max(2, window.devicePixelRatio || 1);
    q = Math.max(1, Math.min(q, Math.sqrt(MAX_PIXELS / (vp.width * vp.height))));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(vp.width * q);
    canvas.height = Math.round(vp.height * q);
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    const text = document.createElement("div");
    text.className = "textLayer";
    p.el.append(canvas, text);
    try {
      p.task = p.pdfPage.render({
        canvasContext: canvas.getContext("2d"), canvas, viewport: vp,
        transform: [q, 0, 0, q, 0, 0], background: "rgb(255,255,255)",
      });
      await p.task.promise;
      if (token !== p.token) return;
      await new pdfjs.TextLayer({ textContentSource: p.pdfPage.streamTextContent(), container: text, viewport: vp }).render();
    } catch (err) {
      if (err?.name !== "RenderingCancelledException" && token === p.token) console.error(err);
    }
  }

  #trackPage() {
    if (!this.pages.length) return;
    const mid = this.box.scrollTop + this.box.clientHeight / 2;
    let i = this.pages.findIndex((p) => p.el.offsetTop + p.el.offsetHeight + MARGIN / 2 > mid);
    i = i < 0 ? this.pages.length - 1 : i;
    if (i !== this.page) { this.page = i; this.onPage(i); }
  }

  goTo(i) {
    if (!(i >= 0 && i < this.pages.length)) return;
    this.page = i;
    this.box.scrollTop = this.pages[i].el.offsetTop - MARGIN;
    this.onPage(i);
  }

  setScale(scale) {
    this.scale = Math.max(0.25 * CSS_PX, Math.min(5 * CSS_PX, scale));
    if (this.pages.length) {
      // keep the same spot of the same page in view
      const p = this.pages[this.page], frac = (this.box.scrollTop - (p.el.offsetTop - MARGIN)) / p.el.offsetHeight;
      this.#layout();
      this.box.scrollTop = p.el.offsetTop - MARGIN + frac * p.el.offsetHeight;
    }
    this.onZoom(this.zoomPercent);
  }

  zoomBy(f) { this.setScale(this.scale * f); }

  fitWidth() {
    if (this.pages.length) this.setScale((this.box.clientWidth - 2 * MARGIN - 20) / this.pages[this.page].size[0]);
  }

  async copySelection() {
    const text = window.getSelection().toString();
    if (!text) return false;
    try { await navigator.clipboard.writeText(text); } catch { document.execCommand("copy"); }
    return true;
  }
}
