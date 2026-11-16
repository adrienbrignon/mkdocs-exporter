from __future__ import annotations

import contextlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from mkdocs_exporter.core.books import Book, BookPrinter
from mkdocs_exporter.core.browser import Browser
from mkdocs_exporter.core.cache import Cache
from mkdocs_exporter.core.document import Document, Layout, Site
from mkdocs_exporter.core.preparation import Prepared
from mkdocs_exporter.core.renderer import Context, Outcome, Renderer, RenderOptions
from mkdocs_exporter.core.server import Server
from mkdocs_exporter.core.themes import Theme
from mkdocs_exporter.logging import Logger

logger = Logger("pdf")


@dataclass
class Report:
    """The outcome of an export."""

    layouts: dict[str, Layout] = field(default_factory=dict)
    """The layout of each document rendered, by document identifier."""

    failures: list[Outcome] = field(default_factory=list)
    """The documents that could not be rendered."""


class Exporter:
    """Renders the documents of a website and combines them."""

    def __init__(
        self,
        site: Site,
        theme: Theme,
        browser: Browser,
        options: RenderOptions | None = None,
        cache: Cache | None = None,
    ) -> None:
        self.site = site
        self.theme = theme
        self.browser = browser
        self.options = options or RenderOptions()
        self.cache = cache

    async def export(
        self, documents: Sequence[Document], books: Sequence[Book] = ()
    ) -> Report:
        """Writes a PDF document for each document, then each book.

        Books are skipped when a document could not be rendered.
        """

        report = Report()
        server = Server(self.site.directory, self.site.prefix)

        async with contextlib.AsyncExitStack() as stack:
            if not self.browser.running:
                # Otherwise, the browser is closed by whoever launched it.
                await stack.enter_async_context(self.browser)

            with server:
                context = Context(
                    self.site, self.theme, self.browser, server, self.options
                )
                renderer = Renderer(context, self.cache)
                # Books reuse the content of pages prepared for their own document.
                keep = {document.id for book in books for document in book.documents}
                outcomes = await renderer.render_all(documents, keep)

                if renderer.reused:
                    logger.info(
                        "Reused %d of %d documents (unchanged)",
                        renderer.reused,
                        len(documents),
                    )

                for outcome in outcomes:
                    if outcome.result is None:
                        report.failures.append(outcome)
                        continue

                    if outcome.result.layout is not None:
                        report.layouts[outcome.document.id] = outcome.result.layout

                    _write(
                        self.site.directory / outcome.document.path, outcome.result.pdf
                    )

                if report.failures:
                    return report

                prepared: dict[str, Prepared] = {}

                for outcome in outcomes:
                    if outcome.prepared is not None:
                        prepared[outcome.document.id] = outcome.prepared
                        # Released once a book has used it.
                        outcome.prepared = None

                for index, book in enumerate(books):
                    printer = BookPrinter(context, book, prepared, f"book-{index}")
                    report.failures += await printer.print()

        return report


def _write(path: Path, data: bytes) -> None:
    """Writes a binary file, creating its directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
