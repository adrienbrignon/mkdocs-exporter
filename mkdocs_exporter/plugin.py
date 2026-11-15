from __future__ import annotations

import os
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError
from mkdocs.livereload import LiveReloadServer
from mkdocs.plugins import BasePlugin, CombinedEvent, event_priority
from mkdocs.structure.files import Files
from mkdocs.structure.nav import Navigation
from mkdocs.structure.pages import Page

from mkdocs_exporter import adapter
from mkdocs_exporter.config import Config
from mkdocs_exporter.core.books import Book, NavNode
from mkdocs_exporter.core.browser import Browser, relaunch
from mkdocs_exporter.core.cache import Cache
from mkdocs_exporter.core.document import Document, Site
from mkdocs_exporter.core.exporter import Exporter
from mkdocs_exporter.core.html import HtmlDocument
from mkdocs_exporter.core.renderer import Outcome
from mkdocs_exporter.core.runner import Loop, run
from mkdocs_exporter.core.themes import Theme, get_theme
from mkdocs_exporter.covers import CoverRenderer
from mkdocs_exporter.formats.pdf.config import BookConfig
from mkdocs_exporter.helpers import resolve
from mkdocs_exporter.logging import logger

MARKERS = ("mkdocs-exporter-only", "data-decompose", "data-teleport")
"""What the website's pages are processed for, besides buttons (see `_decorate_page`)."""


@dataclass
class Export:
    """What is exported for a page."""

    page: Page
    document: Document


class Plugin(BasePlugin[Config]):
    """Exports pages to PDF documents."""

    def __init__(self) -> None:
        self.command = "build"
        self.dirty = False
        self.theme: Theme = Theme()
        self.pdf = False
        self.exports: dict[str, Export] = {}
        self.order: list[str] = []
        self.nav: list[NavNode] = []
        self.watched: set[str] = set()
        self.decomposed = False
        self.covers: CoverRenderer
        self.loop: Loop | None = None
        self.browser: Browser | None = None

    def on_startup(
        self, *, command: Literal["build", "gh-deploy", "serve"], dirty: bool
    ) -> None:
        """Invoked once per process (MkDocs then keeps this instance across rebuilds)."""

        self.command = command
        self.dirty = dirty

        if command == "serve":
            # The browser is kept open from one rebuild to the next.
            self.loop = Loop()

    def on_shutdown(self) -> None:
        """Invoked when MkDocs exits: closes the browser kept while serving."""

        loop, browser = self.loop, self.browser
        self.loop = self.browser = None

        if loop is not None:
            try:
                if browser is not None:
                    loop.run(browser.close)
            finally:
                loop.close()

    @event_priority(100)
    def on_config(self, config: MkDocsConfig) -> None:
        """Invoked when the configuration is loaded: resets the per-build state."""

        if self.config.logging.level:
            logger.setLevel(self.config.logging.level.upper())

        theme = self.config.theme or config.theme
        options = self.config.formats.pdf

        self.theme = get_theme(theme.name)
        self.exports = {}
        self.order = []
        self.nav = []
        self.watched = set()
        self.decomposed = False
        self.covers = CoverRenderer(config)
        self.pdf = options.enabled and (self.command != "serve" or options.serve)

        if options.aggregator.enabled:
            logger.warning(
                "[mkdocs-exporter.pdf] 'formats.pdf.aggregator' is deprecated, list "
                "combined documents in 'formats.pdf.books' instead"
            )

        outputs = [adapter.output(book) for book in adapter.books(options)]

        if len(outputs) != len(set(outputs)):
            raise PluginError(
                "[mkdocs-exporter.pdf] Several books are written to the same file: "
                + ", ".join(sorted({o for o in outputs if outputs.count(o) > 1}))
            )
        if type(self.theme) is Theme:
            logger.info(
                "[mkdocs-exporter] The '%s' theme has no dedicated support, "
                "generic adjustments will be used",
                theme.name,
            )
        if options.enabled and not self.pdf:
            logger.info(
                "[mkdocs-exporter.pdf] PDF documents are not generated while serving "
                "(enable 'formats.pdf.serve' to change this)"
            )

    def on_serve(
        self, server: LiveReloadServer, *, config: MkDocsConfig, builder: Any
    ) -> LiveReloadServer:
        """Watches the files used to generate documents."""

        if self.pdf:
            options = self.config.formats.pdf

            for path in {*options.stylesheets, *options.scripts, *self.watched}:
                server.watch(path)

        return server

    @event_priority(-100)
    def on_nav(self, nav: Navigation, *, config: MkDocsConfig, files: Files) -> None:
        """Records the navigation: its sections and the order of pages."""

        self.nav = adapter.navigation(nav.items)
        self.order = list(
            dict.fromkeys(key for node in self.nav for key in node.documents())
        )

    @event_priority(100)
    def on_pre_page(self, page: Page, *, config: MkDocsConfig, files: Files) -> None:
        """Declares the documents generated for a page."""

        page.formats = {}  # type: ignore[attr-defined]

        if self.pdf:
            path = posixpath.splitext(page.file.dest_uri)[0] + ".pdf"

            page.formats["pdf"] = {  # type: ignore[attr-defined]
                "path": os.path.join(config.site_dir, *path.split("/")),
                "url": path,
                "pages": 0,
                "covers": [],
                "books": [],
            }

    @event_priority(100)
    def _capture_page(self, output: str, *, page: Page, config: MkDocsConfig) -> str:
        """Captures the page's HTML (before other plugins alter it) and its covers."""

        formats: dict[str, Any] = getattr(page, "formats", {})

        if "pdf" in formats and not self._exported(page):
            del formats["pdf"]
        if "pdf" not in formats:
            return output

        templates = self.covers.locations(dict(self.config.formats.pdf.covers), page)
        covers = {
            key: self.covers.render(path, page) for key, path in templates.items()
        }

        self.watched.update(templates.values())
        formats["pdf"]["covers"] = list(covers)
        formats["pdf"]["books"] = self._books_of(page, config)
        self.exports[page.file.src_uri] = Export(
            page=page,
            document=adapter.document(
                page,
                output,
                formats["pdf"]["url"],
                covers,
                self.config.formats.pdf,
                config,
            ),
        )

        return output

    @event_priority(-100)
    def _decorate_page(self, output: str, *, page: Page, config: MkDocsConfig) -> str:
        """Adds buttons to the page and removes what is meant for documents only."""

        buttons = self._buttons(page)

        if not buttons and not any(marker in output for marker in MARKERS):
            return output

        html = HtmlDocument(output)

        for button in buttons:
            attributes = {
                str(key): str(value)
                for key, value in (button.get("attributes") or {}).items()
                if value is not None
            }

            self.theme.button(
                html, str(button["title"]), str(button["icon"]), attributes
            )

        if html.select('[data-decompose="true"]') and not self.decomposed:
            self.decomposed = True
            logger.warning(
                "[mkdocs-exporter] 'data-decompose=\"true\"' is deprecated, give "
                "elements meant for documents only the 'mkdocs-exporter-only' class"
            )

        html.remove([".mkdocs-exporter-only", '[data-decompose="true"]'])
        html.teleport()

        return str(html)

    on_post_page = CombinedEvent(_capture_page, _decorate_page)
    """Captures pages before other plugins, decorates them after."""

    @event_priority(-100)
    def on_post_build(self, *, config: MkDocsConfig) -> None:
        """Generates the PDF documents."""

        if not self.pdf:
            return
        if not self.exports:
            if self.config.formats.pdf.explicit:
                logger.warning(
                    "[mkdocs-exporter.pdf] No page has been rendered: in explicit mode, "
                    "pages must enable PDF generation with 'pdf: true' in their metadata"
                )
            return

        failures = (self.loop.run if self.loop else run)(lambda: self._export(config))

        if failures:
            details = "\n".join(
                f"- {outcome.document.id}: {outcome.error}" for outcome in failures
            )

            raise PluginError(
                f"[mkdocs-exporter.pdf] Failed to render pages:\n{details}"
            )

    async def _export(self, config: MkDocsConfig) -> list[Outcome]:
        """Renders documents and books, returning the failures."""

        options = self.config.formats.pdf
        site = Site(directory=Path(config.site_dir), url=config.site_url or None)
        listed = set(self.order)
        exports = [self.exports[key] for key in self.order if key in self.exports]
        exports += [e for key, e in self.exports.items() if key not in listed]
        books = [self._book(book, config) for book in adapter.books(options)]
        cache = None

        if options.cache.enabled:
            base = Path(config.config_file_path or ".").parent
            cache = Cache(base / options.cache.directory)

        exporter = Exporter(
            site,
            self.theme,
            await self._browser(),
            adapter.render_options(options, config),
            cache,
        )
        report = await exporter.export([e.document for e in exports], books)

        if cache is not None and not report.failures and not self.dirty:
            # Every page was rendered: entries that weren't used are obsolete.
            cache.prune()

        for export in exports:
            if export.document.id in report.layouts:
                formats = getattr(export.page, "formats", {})
                formats["pdf"]["pages"] = report.layouts[export.document.id].pages

        return report.failures

    async def _browser(self) -> Browser:
        """The browser printing documents (kept open while serving)."""

        browser = adapter.browser(self.config.formats.pdf.browser)

        if self.loop is None:
            return browser

        self.browser = await relaunch(self.browser, browser)

        return self.browser

    def _book(self, options: BookConfig, config: MkDocsConfig) -> Book:
        """A book, of the documents of the pages it includes (in navigation order)."""

        documents = [
            self.exports[key].document
            for key in self.order
            if key in self.exports and adapter.includes(options, key)
        ]

        return adapter.book(options, config, documents, self.nav)

    def _books_of(self, page: Page, config: MkDocsConfig) -> list[dict[str, str]]:
        """The books including a page (see `mkdocs_exporter.page.Page`).

        Pages outside the navigation are not part of books.
        """

        books: list[dict[str, str]] = []

        if page.file.src_uri not in self.order:
            return books

        for options in adapter.books(self.config.formats.pdf):
            if adapter.includes(options, page.file.src_uri):
                url = adapter.output(options)
                books.append(
                    {
                        "path": os.path.join(config.site_dir, *url.split("/")),
                        "url": url,
                        "title": adapter.title(options, config),
                    }
                )

        return books

    def _buttons(self, page: Page) -> list[dict[str, Any]]:
        """The enabled buttons of a page, their callables called with the page."""

        return [
            resolve(dict(button), page=page)
            for button in [*self.config.buttons, *page.meta.get("buttons", [])]
            if resolve(button.get("enabled", True), page=page)
        ]

    def _exported(self, page: Page) -> bool:
        """Should a PDF document be generated for the page?"""

        return bool(page.meta.get("pdf", not self.config.formats.pdf.explicit))
