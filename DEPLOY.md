# Hosting DocuBhai Aristocrat Reader on GitHub Pages

The web version is a **static site** in [`web/`](web/) – no server, no build step. Everything (merge, split, sign,
compare, view) runs in the visitor's browser, so PDFs are never uploaded anywhere. All paths are relative, so it works
both at a domain root and under a sub-path.

## Option A (recommended): a project site at `https://rbvk-services.github.io/DocuBhai/`

1. Create a repo named `DocuBhai` under the `rbvk-services` account and push this project to it
   (`git remote add origin https://github.com/rbvk-services/DocuBhai.git && git push -u origin master`).
2. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. Push to `main`/`master` (or run the workflow manually). [`.github/workflows/pages.yml`](.github/workflows/pages.yml)
   runs `npm test`, then publishes the contents of `web/`.
4. Add a link from your main site (`rbvk-services.github.io`), e.g. `<a href="/DocuBhai/">DocuBhai Aristocrat Reader</a>`.

## Option B: serve it from the root user site itself

Copy the **contents** of `web/` into the root of the `rbvk-services.github.io` repository (keep `.nojekyll`) and push.
It then lives at `https://rbvk-services.github.io/`. (This replaces your current home page, so prefer Option A
or put it in a sub-folder such as `docubhai/`, which then lives at `/docubhai/`.)

## Preview locally

```
npm start                              # http://127.0.0.1:8080/
node scripts/serve.mjs 8080 /DocuBhai/ # same, but under the sub-path used on GitHub Pages
```

## Tests

`npm test` (Node 18+) runs the PDF-operation unit tests plus a real-browser smoke test that opens the site under
`/DocuBhai/` in headless Chrome/Edge (skipped if none is found; set `BROWSER_BIN` to point at one).

## Notes

- Third-party code is vendored in `web/vendor/` (pdf-lib – MIT, pdf.js – Apache-2.0; licences included), so the site
  has no CDN dependency. To upgrade, replace those files with the new versions from npm (`pdf-lib`, `pdfjs-dist/legacy`).
- Comic Sans MS is a system font: Windows/macOS show it, other systems fall back to Comic Neue / a cursive font.
