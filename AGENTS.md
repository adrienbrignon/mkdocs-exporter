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
| Tests | `uv run pytest` |
| Build / serve the documentation | `make build` / `make serve` (`PDF=false` or `PDF_AGGREGATOR=false` to speed things up) |
| Build distributions | `uv build` |

Set `NO_MKDOCS_2_WARNING=1` to silence the end-of-life banner Material for MkDocs prints on every build.

Before considering a change done, run the linter, the formatter check, the type checker and the tests.

## Repository layout

| Path | Contents |
|---|---|
| `mkdocs_exporter/plugin.py` | The plugin registered as `exporter`: theme resolution, buttons, page HTML capture |
| `mkdocs_exporter/config.py`, `formats/pdf/config.py` | Configuration schema (MkDocs `config_options`) |
| `mkdocs_exporter/formats/pdf/` | PDF format: plugin events, renderer, browser (Playwright), aggregator (pypdf) |
| `mkdocs_exporter/formats/pdf/buttons/download.py` | Callables referenced from users' `mkdocs.yml` via `!!python/name:` |
| `mkdocs_exporter/formats/pdf/resources/js/` | `pdf.js` (glue with Paged.js) and the vendored Paged.js polyfill |
| `mkdocs_exporter/preprocessor.py` | HTML manipulation helpers (BeautifulSoup + lxml) |
| `mkdocs_exporter/themes/` | Theme-specific adjustments (`material`, `readthedocs`) |
| `docs/`, `mkdocs.yml`, `resources/`, `macros/`, `overrides/` | This project's own documentation site (it dogfoods the plugin) |
| `examples/` | Sample PDF documents linked from the README |

## How it works

1. `on_config`: resolves the theme adapter and registers the PDF sub-plugin (`exporter-pdf`).
2. `on_page_markdown`: cover page templates are injected into the page's Markdown.
3. `on_post_page`: the page's HTML is captured (priority 100, before other plugins), download buttons are
   added to the website's HTML (priority -100) and a rendering task is queued.
4. `on_post_build`: queued pages are rendered concurrently. For each page, the HTML is preprocessed
   (theme cleanup, custom stylesheets and scripts, Paged.js), written to a temporary file, opened in
   Chromium and printed once `pdf.js` reports Paged.js is done.
5. When the aggregator is enabled, every page is rendered again with continuous page numbering and the
   resulting PDF documents are merged.

**Readiness contract:** `pdf.js` sets `body[mkdocs-exporter="true"]` and `body[mkdocs-exporter-pages]` in
Paged.js' `after` hook; Python waits for that attribute before printing. Users can hook into rendering by
defining `window.MkDocsExporter.render` (an async function awaited before pagination).

## Conventions

- Python `>=3.11`, PEP 8 enforced by `ruff format` (88 columns), imports sorted by ruff.
- Type hints on all new code; keep `mypy` clean.
- Docstrings on public classes and functions.
- Log through `mkdocs_exporter.logging.logger`; prefix messages with `[mkdocs-exporter.<area>]`.
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

## Vendored Paged.js

`mkdocs_exporter/formats/pdf/resources/js/pagedjs.min.js` is the Paged.js **v0.4.3** polyfill build (the
latest stable release). Do not edit it by hand. To update it, replace it with
`https://unpkg.com/pagedjs@<version>/dist/paged.polyfill.min.js`, then run the full test suite (including
browser tests) and compare a few generated PDF documents. Resource files are marked `-diff` in
`.gitattributes`.

## Releasing

1. Update the version: `uv version <x.y.z>`.
2. Update the changelog and the documentation.
3. Tag `v<x.y.z>` and push the tag: the `Release` workflow builds, publishes to PyPI (trusted publishing)
   and creates the GitHub release.
