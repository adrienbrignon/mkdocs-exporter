"""The MkDocs plugin (registered as `exporter`)."""

from __future__ import annotations

import os
import posixpath
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError
from mkdocs.livereload import LiveReloadServer
from mkdocs.plugins import BasePlugin, CombinedEvent, event_priority
from mkdocs.structure.files import Files
from mkdocs.structure.nav import Navigation, Section
from mkdocs.structure.pages import Page

from mkdocs_exporter.config import Config
from mkdocs_exporter.core.aggregator import Aggregation
from mkdocs_exporter.core.browser import Browser
from mkdocs_exporter.core.document import Document, Site
from mkdocs_exporter.core.exporter import Exporter
from mkdocs_exporter.core.html import HtmlDocument
from mkdocs_exporter.core.renderer import Outcome, RenderOptions
from mkdocs_exporter.core.runner import run
from mkdocs_exporter.core.themes import Theme, get_theme
from mkdocs_exporter.covers import CoverRenderer
from mkdocs_exporter.helpers import resolve
from mkdocs_exporter.logging import logger


@dataclass
class Export:
    """What is exported for a page."""

    page: Page
    document: Document


class Plugin(BasePlugin[Config]):
    """Exports pages to PDF documents."""

    def __init__(self) -> None:
        self.command = "build"
        self.theme: Theme = Theme()
        self.pdf = False
        self.exports: dict[str, Export] = {}
        self.order: list[str] = []
        self.watched: set[str] = set()
        self.covers: CoverRenderer

    def on_startup(
        self, *, command: Literal["build", "gh-deploy", "serve"], dirty: bool
    ) -> None:
        """Invoked once per process (MkDocs then keeps this instance across rebuilds)."""

        self.command = command

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
        self.watched = set()
        self.covers = CoverRenderer(config)
        self.pdf = options.enabled and (self.command != "serve" or options.serve)

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
        """Records the order of the pages in the navigation."""

        def walk(items: Sequence[Any]) -> list[str]:
            pages: list[str] = []

            for item in items:
                if isinstance(item, Page) and item.file is not None:
                    pages.append(item.file.src_uri)
                elif isinstance(item, Section):
                    pages.extend(walk(item.children))

            return pages

        self.order = list(dict.fromkeys(walk(nav.items)))

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
        self.exports[page.file.src_uri] = Export(
            page=page,
            document=Document(
                id=page.file.src_uri,
                url=page.url,
                path=formats["pdf"]["url"],
                title=page.title or "",
                html=output,
                meta=dict(page.meta),
                covers=covers,
            ),
        )

        return output

    @event_priority(-100)
    def _decorate_page(self, output: str, *, page: Page, config: MkDocsConfig) -> str:
        """Adds buttons to the page and removes what is meant for documents only."""

        buttons = [
            button
            for button in [*self.config.buttons, *page.meta.get("buttons", [])]
            if resolve(button.get("enabled", True), page=page)
        ]

        if (
            not buttons
            and "data-decompose" not in output
            and "data-teleport" not in output
        ):
            return output

        html = HtmlDocument(output)

        for button in buttons:
            options = resolve(dict(button), page=page)
            attributes = {
                str(key): str(value)
                for key, value in (options.get("attributes") or {}).items()
                if value is not None
            }

            self.theme.button(
                html, str(options["title"]), str(options["icon"]), attributes
            )

        html.remove('[data-decompose="true"]')
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

        failures = run(lambda: self._export(config))

        if failures:
            details = "\n".join(
                f"- {outcome.document.id}: {outcome.error}" for outcome in failures
            )

            raise PluginError(
                f"[mkdocs-exporter.pdf] Failed to render pages:\n{details}"
            )

    async def _export(self, config: MkDocsConfig) -> list[Outcome]:
        """Renders and aggregates documents, returning the failures."""

        options = self.config.formats.pdf
        site = Site(directory=Path(config.site_dir), url=config.site_url or None)
        links = options.url or config.site_url or None
        exports = [self.exports[key] for key in self.order if key in self.exports]
        exports += [e for key, e in self.exports.items() if key not in set(self.order)]
        aggregations = []

        if options.aggregator.enabled:
            aggregations.append(
                Aggregation(
                    output=options.aggregator.output.replace(os.sep, "/"),
                    documents=[
                        self.exports[key].document
                        for key in self.order
                        if key in self.exports
                    ],
                    covers=options.aggregator.covers,
                    metadata={
                        "title": config.site_name,
                        "author": config.site_author,
                        **options.aggregator.metadata,
                    },
                )
            )

        exporter = Exporter(
            site,
            self.theme,
            Browser(
                headless=options.browser.headless,
                timeout=options.browser.timeout,
                args=options.browser.args,
                channel=options.browser.channel,
                debug=options.browser.debug,
            ),
            RenderOptions(
                stylesheets=[_read(path) for path in options.stylesheets],
                scripts=[_read(path) for path in options.scripts],
                links=links if links is None or links.endswith("/") else links + "/",
                delay=options.browser.delay,
                concurrency=options.concurrency,
            ),
        )
        report = await exporter.export([e.document for e in exports], aggregations)

        for export in exports:
            if export.document.id in report.layouts:
                formats = getattr(export.page, "formats", {})
                formats["pdf"]["pages"] = report.layouts[export.document.id].pages

        return report.failures

    def _exported(self, page: Page) -> bool:
        """Should a PDF document be generated for the page?"""

        return bool(page.meta.get("pdf", not self.config.formats.pdf.explicit))


def _read(path: str) -> str:
    """Reads a text file."""

    with open(path, encoding="utf-8") as file:
        return file.read()
