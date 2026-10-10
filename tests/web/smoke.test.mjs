// Real-browser sanity check: loads the actual site (under a /DocuBhai/ subpath, like GitHub project pages)
// in headless Edge/Chrome and drives it through tests/web/harness/smoke.html. Skipped if no browser is found.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { startServer } from "../../scripts/serve.mjs";

const BROWSERS = [
  process.env.BROWSER_BIN,
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
].filter(Boolean);
const browser = BROWSERS.find((p) => existsSync(p));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Poll the page's #result element over the DevTools protocol until the harness has finished. */
async function readResult(debugPort, deadline) {
  let target;
  while (!target && Date.now() < deadline) {
    try {
      target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find((t) => t.url.includes("smoke.html"));
    } catch { /* browser still starting */ }
    if (!target) await sleep(200);
  }
  assert.ok(target, "browser never opened the smoke page");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0;
  const evaluate = (expression) => new Promise((resolve) => {
    const mine = ++id;
    ws.addEventListener("message", function on(e) {
      const msg = JSON.parse(e.data);
      if (msg.id === mine) { ws.removeEventListener("message", on); resolve(msg.result?.result?.value ?? ""); }
    });
    ws.send(JSON.stringify({ id: mine, method: "Runtime.evaluate", params: { expression } }));
    setTimeout(() => resolve("UNRESPONSIVE"), 5000); // a frozen page (e.g. a blocking alert) must fail, not hang
  });
  try {
    while (Date.now() < deadline) {
      const text = await evaluate("document.getElementById('result')?.textContent");
      assert.notEqual(text, "UNRESPONSIVE", "the page froze (blocking alert or infinite loop?)");
      if (text.startsWith("RESULT:")) return JSON.parse(text.slice(7, -4));
      await sleep(300);
    }
  } finally {
    ws.close();
  }
  throw new Error("smoke page did not finish in time");
}

test("site works end-to-end in a real browser", { skip: !browser && "no Chrome/Edge found (set BROWSER_BIN)", timeout: 120_000 }, async () => {
  const server = await startServer({ base: "/DocuBhai/", withTests: true });
  const profile = mkdtempSync(join(tmpdir(), "docubhai-smoke-"));
  const debugPort = 9300 + Math.floor(Math.random() * 500);
  const proc = spawn(browser, [
    "--headless=new", "--disable-gpu", "--no-first-run", ...(process.env.CI ? ["--no-sandbox"] : []), `--user-data-dir=${profile}`,
    `--remote-debugging-port=${debugPort}`, `http://127.0.0.1:${server.address().port}/__tests__/smoke.html`,
  ], { stdio: "ignore" });
  try {
    const results = await readResult(debugPort, Date.now() + 90_000);
    const failed = Object.entries(results).filter(([, v]) => v !== "ok");
    assert.deepEqual(failed, [], "failed checks: " + JSON.stringify(failed));
    assert.ok(Object.keys(results).length >= 15, "too few checks ran: " + Object.keys(results).join());
  } finally {
    proc.kill();
    server.close();
    await sleep(500);
    try { rmSync(profile, { recursive: true, force: true }); } catch { /* browser may still hold files */ }
  }
});
