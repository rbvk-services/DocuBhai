// Tiny static file server for local preview:  node scripts/serve.mjs [port] [base-path]
// e.g. `node scripts/serve.mjs 8080 /DocuBhai/` mimics hosting as a GitHub project site.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { extname, join, normalize, sep } from "node:path";

const ROOT = fileURLToPath(new URL("../web/", import.meta.url));
const TESTS = fileURLToPath(new URL("../tests/web/harness/", import.meta.url));
const TYPES = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".png": "image/png", ".ico": "image/x-icon", ".json": "application/json", ".ttf": "font/ttf",
};

export function startServer({ port = 0, base = "/", withTests = false } = {}) {
  const server = createServer(async (req, res) => {
    let path = decodeURIComponent(new URL(req.url, "http://x").pathname), dir = ROOT;
    if (withTests && path.startsWith("/__tests__/")) { dir = TESTS; path = path.slice("/__tests__".length); }
    else if (path.startsWith(base)) path = "/" + path.slice(base.length);
    else { res.writeHead(404).end("Not found (outside base path)"); return; }
    if (path.endsWith("/")) path += "index.html";
    const file = normalize(join(dir, path));
    if (!file.startsWith(dir.replace(/[\\/]$/, "") + sep)) { res.writeHead(403).end(); return; }
    try {
      res.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream" }).end(await readFile(file));
    } catch {
      res.writeHead(404).end("Not found");
    }
  });
  return new Promise((resolve) => server.listen(port, "127.0.0.1", () => resolve(server)));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [port = 8080, base = "/"] = process.argv.slice(2);
  const s = await startServer({ port: +port, base });
  console.log(`DocuBhai Aristocrat Reader: http://127.0.0.1:${s.address().port}${base}`);
}
