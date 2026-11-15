# AGENTS.md

Guidance for AI coding agents (and humans) working on this repository.

## Project

*MkDocs Exporter* is an MkDocs plugin (entry point `exporter`) that exports documentation pages to PDF.
Each page is printed by a headless Chromium driven by [Playwright](https://playwright.dev/python/),
using the browser's own CSS Paged Media support (page sizes, margin boxes, page counters, named pages).
Pages can also be combined into a single PDF document (aggregator, with
[pypdf](https://pypdf.readthedocs.io/) for bookmarks and links). Paged.js is not bundled anymore: users
can load it through `formats.pdf.scripts` (documented recipe).

Supported hosts: MkDocs `>=1.6,<2` and [ProperDocs](https://github.com/ProperDocs/properdocs) (a MkDocs
1.x fork that runs MkDocs plugins unchanged). MkDocs 2.0 has no plugin API and Zensical silently ignores
third-party plugins, so neither is supported as a plugin host.

## Commands

| Task | Command |
|---|---|
| Install dependencies | `uv sync` |
| Install the browser | `uv run playwright install --only-shell chromium` (add `--with-deps` on a fresh Linux/CI machine; needs root) |
| Lint | `uv run ruff check` |
| Format | `uv run ruff format` |
| Type check | `uv run mypy` |
| Tests | `uv run pytest` (`-m "not browser"` to skip the end-to-end tests; `--cov` for coverage, which fails under 85 % without them) |
| Tests on ProperDocs | `MKDOCS_EXPORTER_TEST_PROPERDOCS=1 uv run --with properdocs --with properdocs-theme-mkdocs --with properdocs-theme-readthedocs pytest` |
| Build / serve the documentation | `make build` / `make serve` (`PDF=false` or `PDF_AGGREGATOR=false` to speed things up) |
| Build distributions | `uv build` |

Set `NO_MKDOCS_2_WARNING=1` to silence the end-of-life banner Material for MkDocs prints on every build.

Before considering a change done, run the linter, the formatter check, the type checker and the tests.

## Repository layout

| Path | Contents |
|---|---|
| `mkdocs_exporter/core/` | **Engine-agnostic core** (must never import `mkdocs`, enforced by ruff `TID251`) |
| `core/document.py` | `Site` and `Document`: the plain data the core works on |
| `core/html.py` | HTML manipulation (BeautifulSoup + lxml), link resolution |
| `core/server.py` | Loopback HTTP server exposing the built site (and in-memory pages) to the browser |
| `core/browser.py` | Playwright/Chromium: prints a URL to PDF, collects diagnostics |
| `core/renderer.py` | Prepares a page's print HTML and renders documents concurrently |
| `core/exporter.py` | Orchestrates an export: server, browser, documents, then aggregations |
| `core/aggregator.py` | Combined documents: printing, measurements, table of contents, bookmarks (pypdf) |
| `core/book.py` | Combined documents assembled as a single HTML document (parts, URLs, identifiers, named pages) |
| `core/margins.py` | Headers and footers compiled to CSS page margin boxes |
| `core/themes/` | Theme adapters (`material`, `readthedocs`, generic fallback) |
| `core/resources/` | `pdf.js` (gets pages ready, reports readiness), `book.js` (measures combined documents), theme scripts, print CSS, TOC template |
| `core/runner.py` | Runs coroutines on an event loop owned by the exporter (`Loop`: kept across `serve` rebuilds) |
| `core/cache.py` | Cache of printed documents (`.cache/plugin/exporter`), checked against the resources they loaded |
| `mkdocs_exporter/plugin.py` | The MkDocs plugin (`exporter`): adapts MkDocs pages and navigation to core data |
| `mkdocs_exporter/covers.py` | Renders cover templates with Jinja (through mkdocs-macros when enabled) |
| `mkdocs_exporter/config.py`, `formats/pdf/config.py` | Configuration schema (MkDocs `config_options`) |
| `mkdocs_exporter/formats/pdf/buttons/download.py` | Callables referenced from users' `mkdocs.yml` via `!!python/name:` |
| `tests/unit/`, `tests/integration/` | Unit tests; end-to-end tests building `tests/fixtures/site` (marker `browser`) |
| `docs/`, `mkdocs.yml`, `resources/`, `macros/`, `overrides/` | This project's own documentation site (it dogfoods the plugin) |

## How it works

1. `on_startup` / `on_config`: the theme adapter is resolved and per-build state is reset (MkDocs keeps
   the plugin instance across `mkdocs serve` rebuilds because it defines `on_startup`). PDF documents are
   not generated while serving unless `formats.pdf.serve` is enabled; then the browser is kept open on a
   `Loop` thread until `on_shutdown` (with a fresh browser context for each build).
2. `on_nav` records the navigation (order, sections); `on_pre_page` declares `page.formats["pdf"]`.
3. `on_post_page`: the page's HTML is captured and its cover templates rendered (priority 100, before
   other plugins), then buttons are added to the website's HTML (priority -100).
4. `on_post_build` (priority -100, after other plugins wrote their files): the core `Exporter` starts a
   `Server` exposing the site directory and a `Browser`, and the `Renderer` prints every page
   concurrently. Each page's print HTML (covers, stylesheets, headers/footers, scripts) is served from
   memory at the page's own URL (with a query string), so relative URLs resolve. Unchanged documents are
   reused from the cache: the key is a fingerprint of the page and options (before preparing it), and an
   entry is valid while the same-origin resources the page loaded hash the same.
5. Each aggregation is printed as a single HTML document (`core/book.py`): the first page's shell holding
   one part per page (the page's content element, with its kept covers), reusing the content the
   renderer prepared (only the shell is parsed again). Relative URLs become root-absolute, links to
   other parts anchors, identifiers (and radio groups) are prefixed by part (`p2-`); covers, the table
   of contents, blank pages and each part's content (for `{page_title}`) are on named pages, styles
   teleported by covers are translated (`@page :first` → covers' named page) and scoped (`@scope`) to
   their part when they differ. A draft print (`page_ranges="1"`: the whole document is laid out, only
   one page is painted) is measured by `book.js`; the aggregator patches the document (table of contents,
   blank pages for `start: odd`, `{section}` counter style) and prints it again, checking the final
   print's measurement (up to 3 times). Bookmarks are added with pypdf from that measurement, and named
   destinations are lowered by the top margin of their page.

**Browser contract** (see `core/resources/js/pdf.js`): `pdf.js` is the first script of the page. It
records uncaught errors by phase, waits for the `load` event, fonts, images, MathJax and the theme
(`window.MkDocsExporterTheme.settle`), runs the `window.MkDocsExporter.before/render/after` hooks, then
sets `body[mkdocs-exporter]` to `true` or `error` and resolves `window.__MKDOCS_EXPORTER_READY__` (awaited by
`Browser.print` in a single round-trip).

**Layout data** of single documents comes from the printed PDF: hidden links to every heading make
Chromium create named destinations (`core/pdf.py:read_layout`). Combined documents are measured while
they are printed (`book.js`, from a `matchMedia('print')` listener: the print layout is live there, the
root element having one fragment per page). Features browsers lack are computed from a first print:
`{section}` running heads become a `@counter-style` with one symbol per page
(`Browser.print(refine=...)` patches the page and prints again).

Design decisions backed by measurements (don't revert them without measuring again):

- **Loopback HTTP server**, not Playwright routing (+55 % per page) nor `file://` (broken absolute paths,
  CORS, fetches).
- **Native printing, no Paged.js**: about 2.4x faster per page than Paged.js; missing
  features (running heads, TOC page numbers) are rebuilt from a measuring print.
- **Hide theme chrome with CSS**: removing it from the DOM breaks the theme's scripts. Exception:
  `Theme.removed` (Material's search box, whose index would otherwise be loaded by every page).
- **Prepare pages on the event loop**, not in a thread: BeautifulSoup work waits for the GIL in a thread
  (about 5x slower at concurrency 4). Preparing pages is now the main cost of a build.
- **Chromium shrinks every page** when anything overflows horizontally or when flex containers start on a
  page of another width: `base.css` clips overflow on `body > *` and lays out the ancestors of the content
  (marked `data-mkdocs-exporter-ancestor`) as blocks, for any theme.
- **The canvas hides page backgrounds**: `pdf.js` moves the background of `html`/`body` (and the body's
  font, which margin boxes don't inherit) to a `@page` rule, `base.css` makes them transparent in print.
- **Combined documents are a single HTML document printed once**, not every page rendered again and
  merged with pypdf: on the 201-page project, 3.4 s instead of 9.6 s (6.4 s when parsing every page
  again: keeping the renderer's prepared content halves the cost); 2.3 s for 800 text-only pages against
  29 s for the per-page approach with Paged.js. The draft print costs a quarter to a third of a full
  one (0.9 s instead of 2.6 s for the 829 pages of the 201-page project, 2.8 s instead of 11.7 s for
  925 pages heavy with code); `@counter-style` with 5,000 symbols adds 2 % to a print.
  Native printing is superlinear beyond a few thousand pages (5,000 trivial pages: 6 s; 20,000: 180 s).
- **A change of named page starts a new page**, even for an empty box: `body` and each part are given the
  name of their first page and parts lose their pseudo-elements, else books get blank pages.
- **`wait_until="load"`**: identical output to `networkidle`, about 35 % faster.
- Uncaught errors of the website's scripts are logged at debug level (they also happen on the website);
  errors in `MkDocsExporter` hooks and missing same-origin resources are warnings; only pagination failures
  and timeouts fail the build.

## Conventions

- Python `>=3.11`, PEP 8 enforced by `ruff format` (88 columns), imports sorted by ruff.
- Type hints on all new code; keep `mypy` clean.
- Docstrings on public classes and functions.
- Log through `mkdocs_exporter.logging.logger`; prefix messages with `[mkdocs-exporter.<area>]`.
- Keep the core free of `mkdocs` imports: it is meant to be driven by other engines (a standalone
  command for Zensical and MkDocs 2.0 is planned).
- Do not use `asyncio.get_event_loop()` / `asyncio.set_event_loop()`: the plugin runs inside other tools'
  processes (`mkdocs serve`, other plugins, notebooks).
- MkDocs reuses plugin instances across rebuilds (`mkdocs serve`): reset per-build state in `on_config` /
  `on_pre_build`, never in `__init__` alone.
- Keep these public surfaces stable (or deprecate them explicitly):
  - the `exporter` entry point and documented configuration keys;
  - `mkdocs_exporter.formats.pdf.buttons.download.*` and `mkdocs_exporter.page.Page`;
  - the `window.MkDocsExporter` JavaScript hooks and the `mkdocs-exporter-*` CSS classes.
- Commits follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`,
  `refactor:`, `test:`, `build:`, `ci:`, `chore:`, `style:`); mark breaking changes with `!` and a
  `BREAKING CHANGE:` footer; reference issues with `Fixes #N` / `Refs #N`.
- Formatting-only commits go into `.git-blame-ignore-revs`.

## Testing

- Unit tests (`tests/unit/`) cover pure logic; prefer them for anything in `core/` that doesn't need a
  browser.
- Integration tests (`tests/integration/`, marker `browser`) copy `tests/fixtures/site` and build it:
  `project.build(exporter={...}, **mkdocs_config)` merges options into the defaults of
  `tests/conftest.py`; `project.serve(builds=2, dirty=False)` reproduces `mkdocs serve` rebuilds;
  `project.write(path, content)` customizes the project first.
- Inspect output with `site.pdf(path)` (`tests/support/pdf.py`): text per page, links, outline, metadata,
  images. Never compare PDF bytes (pypdf output isn't deterministic).
- A known, unfixed bug gets a test marked `@pytest.mark.xfail(reason="#N: ...")`; xfail is strict, so the
  fix must remove the marker.
- Browser tests are skipped when Chromium is missing, except on CI (`CI` set) where they fail.

## Releasing

1. Update the version: `uv version <x.y.z>`.
2. Update the changelog and the documentation.
3. Tag `v<x.y.z>` and push the tag: the `Release` workflow builds, publishes to PyPI (trusted publishing)
   and creates the GitHub release.
