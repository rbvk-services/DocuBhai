# DocuBhai Aristocrat Reader

A small PDF toolbox with a Windows 2003 look (Comic Sans included): **merge, split, sign, compare and read PDFs.**

- **Web version:** https://rbvk-services.github.io/DocuBhai/ (runs in your browser; your PDFs never leave your computer)
- **Desktop version:** a Python + Qt app

## Features

| Tab | What it does |
|---|---|
| Merge | Combine several PDFs in any order (drag to reorder) |
| Split | Cut a PDF into parts, e.g. pages `1-3,5`, or one file per page |
| Sign | Stamp a typed signature on a page, in any corner |
| Compare | Show which lines of text differ between two PDFs |
| View | Read a PDF: continuous scroll, zoom, page jump, select and copy text |

## Run it

**Desktop (Python 3.10+):**
```
pip install -r requirements.txt
python app.py
python -m pytest -q          # tests
```

**Web (Node 18+ only needed for the preview and tests):**
```
npm start                    # preview at http://127.0.0.1:8080/
npm test                     # unit tests + a real-browser smoke test
```
Or just open the live site above. To publish your own copy, see [DEPLOY.md](DEPLOY.md).

---

# How it works, explained simply

## Two copies of one app

| | Desktop app | Web app |
|---|---|---|
| Language | Python | JavaScript |
| Runs on | your computer | any browser |
| Code | `app.py`, `viewer.py`, `pdf_ops.py` | the `web/` folder |

Why two? GitHub Pages (the website host) can only hand out **plain files**. It can't run Python. So the web copy is the same app rewritten in the language browsers understand.

## What is a "workflow"?

A **workflow** is a to-do list for a robot at GitHub. Every time code is pushed, the robot follows the list. Ours is `.github/workflows/pages.yml`.

### How ours differs from GitHub's suggested workflows

Think of publishing a website like **selling cakes**:

| Workflow | Meaning | Cake version |
|---|---|---|
| Next.js, Nuxt, Hugo, Gatsby, Jekyll | Your code is a *recipe* that must be **built** into a website | The robot bakes the cake, then sells it |
| Static HTML (the closest one) | Your files are already finished | The cake is baked; put it in the shop window |
| **Ours** | Finished files **plus a taste test first** | Taste it. Only if it's good, put it in the window |

Ours differs in three ways:

1. **No building.** `web/` is already a finished website.
2. **Tests run first.** If any fail, nothing is published, so a broken site never goes live.
3. **Only `web/` is published.** The Python app and tests are not served to visitors.

```
push code  ->  [test]  ->  [deploy]  ->  site is live
                 |
          fails? stop here
```

## Project layout

```
DocuBhai/
├── pdf_ops.py, viewer.py, app.py   Desktop app (Python + Qt)
├── tests/                          Python tests (pytest) + web tests (Node)
├── web/                            THE WEBSITE (this is what gets published)
│   ├── index.html                  page structure (tabs, buttons)
│   ├── style.css                   the Windows 2003 look
│   ├── js/pdfops.js                merge / split / sign / compare
│   ├── js/viewer.js                the PDF reader (scroll, zoom, select text)
│   ├── js/app.js                   connects buttons to the code above
│   └── vendor/                     two ready-made libraries (below)
├── .github/workflows/pages.yml     the robot's to-do list
└── ARCHITECTURE.md, DEPLOY.md      deeper technical notes
```

## How the web app works

```
  You click a button
        |
    app.js      (the "waiter": takes your order)
     |      |
 pdfops.js  viewer.js   (the "kitchen": does the PDF work)
     |      |
  pdf-lib   pdf.js      (ready-made tools: edit PDFs / draw PDFs)
        |
  result shows up or downloads, all inside YOUR browser
```

- **Privacy:** there is no server receiving your PDFs.
- **Vendored libraries:** `pdf-lib` and `pdf.js` are copied into `web/vendor/`, so the site doesn't depend on anyone else's servers.

## How it gets online

```
your computer --git push--> GitHub repo --robot (workflow)--> GitHub Pages --> rbvk-services.github.io/DocuBhai/
```

## Words you might meet

- **Static site:** a website made only of files, with no program running behind it.
- **Repo:** the project folder stored on GitHub.
- **Push:** upload your latest changes to GitHub.
- **Deploy:** copy the finished site to where visitors can see it.
- **Vendored:** a library copied into your project instead of loaded from the internet.
- **Environment protection rule:** GitHub's "only these branches may publish" setting.

## More detail

- [ARCHITECTURE.md](ARCHITECTURE.md): technical design of the desktop and web apps
- [DEPLOY.md](DEPLOY.md): hosting steps for GitHub Pages

## Credits and licences

Uses [pdf-lib](https://github.com/Hopding/pdf-lib) (MIT) and [pdf.js](https://github.com/mozilla/pdf.js) (Apache-2.0) in the web version; licences are in `web/vendor/`.
Agent skills in `.claude/skills/` are from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
