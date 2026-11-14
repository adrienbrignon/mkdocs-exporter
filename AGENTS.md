# AGENTS.md

Guidance for AI coding agents (and humans) working on this repository.

## Project

*MkDocs Exporter* is an MkDocs plugin (entry point `exporter`) that exports documentation pages to PDF.
Each page is printed by a headless Chromium driven by [Playwright](https://playwright.dev/python/),
with the [Paged.js](https://pagedjs.org/) polyfill providing CSS Paged Media (page sizes, margin boxes,
running headers, page counters). Pages can also be combined into a single PDF document (aggregator,
built on [pypdf](https://pypdf.readthedocs.io/)).

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
| Tests | `uv run pytest` (`-m "not browser"` to skip the end-to-end tests) |
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
| `core/aggregator.py` | Cover selection, page numbering and merging of the combined document (pypdf) |
| `core/themes/` | Theme adapters (`material`, `readthedocs`, generic fallback) |
| `core/resources/` | `pdf.js` (Paged.js driver), theme scripts, print CSS, vendored Paged.js |
| `core/runner.py` | Runs coroutines on an event loop owned by the exporter |
| `mkdocs_exporter/plugin.py` | The MkDocs plugin (`exporter`): adapts MkDocs pages to core documents |
| `mkdocs_exporter/config.py`, `formats/pdf/config.py` | Configuration schema (MkDocs `config_options`) |
| `mkdocs_exporter/formats/pdf/buttons/download.py` | Callables referenced from users' `mkdocs.yml` via `!!python/name:` |
| `tests/unit/`, `tests/integration/` | Unit tests; end-to-end tests building `tests/fixtures/site` (marker `browser`) |
| `docs/`, `mkdocs.yml`, `resources/`, `macros/`, `overrides/` | This project's own documentation site (it dogfoods the plugin) |

## How it works

1. `on_startup` / `on_config`: the theme adapter is resolved and per-build state is reset (MkDocs keeps
   the plugin instance across `mkdocs serve` rebuilds because it defines `on_startup`). PDF documents are
   not generated while serving unless `formats.pdf.serve` is enabled.
2. `on_nav` records the navigation order; `on_pre_page` declares `page.formats["pdf"]`;
   `on_page_markdown` injects cover pages into the Markdown.
3. `on_post_page`: the page's HTML is captured (priority 100, before other plugins), then buttons are
   added to the website's HTML and cover pages removed from it (priority -100).
4. `on_post_build` (priority -100, after other plugins wrote their files): a `Server` exposes the site
   directory, a `Browser` is launched and the `Renderer` prints every page concurrently. Each page's print
   HTML is served from memory at the page's own URL (with a query string), so relative URLs resolve.
5. The aggregator plans the combined document from the measured layouts (removed covers, page offsets),
   renders the pages again with continuous numbering (again if a page count changed) and merges them.

**Browser contract** (see `core/resources/js/pdf.js`): `pdf.js` is the first script of the page. It
records uncaught errors by phase, loads Paged.js after the website's scripts initialized (`load` event),
runs `window.MkDocsExporter.before/render` hooks, flattens shadow trees, removes hidden elements,
paginates (`PagedConfig.auto = false`), then sets `body[mkdocs-exporter]` to `true` or `error`.

Design decisions backed by measurements (don't revert them without measuring again):

- **Loopback HTTP server**, not Playwright routing (+55 % per page) nor `file://` (broken absolute paths,
  CORS, fetches).
- **Hide theme chrome with CSS, remove it right before pagination**: removing it from the DOM up front
  breaks the theme's scripts; leaving it in the DOM makes Paged.js repeat `position: fixed` elements on
  every page.
- **Load Paged.js after the website's scripts**: its polyfills break some of them (Bootstrap modals).
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

## Vendored Paged.js

`mkdocs_exporter/core/resources/js/pagedjs.min.js` is the Paged.js **v0.4.3** polyfill build (the
latest stable release). Do not edit it by hand. To update it, replace it with
`https://unpkg.com/pagedjs@<version>/dist/paged.polyfill.min.js`, then run the full test suite (including
browser tests) and compare a few generated PDF documents. Resource files are marked `-diff` in
`.gitattributes`.

## Releasing

1. Update the version: `uv version <x.y.z>`.
2. Update the changelog and the documentation.
3. Tag `v<x.y.z>` and push the tag: the `Release` workflow builds, publishes to PyPI (trusted publishing)
   and creates the GitHub release.
