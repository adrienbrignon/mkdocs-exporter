"""Renders documents to PDF."""

from __future__ import annotations

import asyncio
import importlib.resources
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from mkdocs_exporter.core.browser import Browser, PrintResult, RenderError
from mkdocs_exporter.core.document import Document, Site
from mkdocs_exporter.core.html import HtmlDocument, resolve_link
from mkdocs_exporter.core.pdf import RELATIVE_LINKS_BASE, relativize_links
from mkdocs_exporter.core.server import RESERVED, Server
from mkdocs_exporter.core.themes import Theme
from mkdocs_exporter.logging import logger

COVER_LOCATIONS = ("front", "back")
"""The locations of cover pages."""


@dataclass
class RenderOptions:
    """Options of the renderer."""

    stylesheets: Sequence[str] = ()
    """Contents of the stylesheets applied to every document."""

    scripts: Sequence[str] = ()
    """Contents of the scripts injected into every document."""

    links: str | None = None
    """The URL replacing the website's root in links (`None` for relative links)."""

    delay: int = 0
    """Extra time (in milliseconds) given to scripts before pagination."""

    concurrency: int = 4
    """The maximum number of documents rendered at once."""

    hidden: Sequence[str] = (".mkdocs-exporter-ignore",)
    """Selectors of elements that must not appear in documents (besides the theme's)."""


@dataclass
class Pass:
    """Parameters of a rendering pass."""

    covers: Iterable[str] | None = None
    """The cover pages to keep (`None` to keep them all)."""

    page: int | None = None
    """The number of the document's first page (aggregated documents)."""

    pages: int | None = None
    """The total number of pages (aggregated documents)."""

    name: str = "default"
    """A name, unique for each pass."""

    directory: str | None = None
    """The directory relative links are resolved from (defaults to the document's)."""


@dataclass
class Outcome:
    """The outcome of rendering a document."""

    document: Document
    result: PrintResult | None = None
    error: RenderError | None = None
    warnings: list[str] = field(default_factory=list)


class Renderer:
    """Renders documents to PDF with a browser, through a server exposing the website."""

    def __init__(
        self,
        site: Site,
        theme: Theme,
        browser: Browser,
        server: Server,
        options: RenderOptions | None = None,
    ) -> None:
        self.site = site
        self.theme = theme
        self.browser = browser
        self.server = server
        self.options = options or RenderOptions()

        from mkdocs_exporter.core.resources import css

        self.stylesheets = [
            importlib.resources.files(css)
            .joinpath("base.css")
            .read_text(encoding="utf-8"),
            theme.print_stylesheet(),
            *self.options.stylesheets,
        ]

    def prepare(self, document: Document, render_pass: Pass | None = None) -> str:
        """Returns the HTML to print for a document."""

        render_pass = render_pass or Pass()
        html = HtmlDocument(document.html)
        hidden = [*self.theme.hidden, *self.options.hidden]
        base = self.options.links or RELATIVE_LINKS_BASE

        if render_pass.covers is not None:
            for location in set(COVER_LOCATIONS) - set(render_pass.covers):
                html.remove(f"div.mkdocs-exporter-{location}-cover")

        html.set_attribute("details:not([open])", "open", "")
        html.teleport()

        for stylesheet in self.stylesheets:
            if stylesheet:
                html.add_style(self.theme.transform_stylesheet(stylesheet))

        if hidden:
            html.add_style(", ".join(hidden) + " { display: none !important; }")

        # Inserted first in the head (hence in reverse order) to run before any script of
        # the website, so that errors are recorded from the start (Paged.js is loaded by
        # `pdf.js` itself, once the website's scripts have initialized).
        if theme_script := self.theme.print_script():
            html.add_script(theme_script, head=True, first=True)

        html.add_script(src=RESERVED + "pdf.js", head=True, first=True)
        html.add_data(
            "__MKDOCS_EXPORTER__",
            {
                "pagedjs": RESERVED + "pagedjs.min.js",
                "hide": hidden,
                "delay": self.options.delay,
                "page": render_pass.page,
                "pages": render_pass.pages,
            },
            head=True,
            first=True,
        )

        for script in self.options.scripts:
            html.add_script(script)

        html.rewrite_links(
            lambda href: resolve_link(href, document.url, self.site.prefix, base)
        )

        return str(html)

    async def render(
        self, document: Document, render_pass: Pass | None = None
    ) -> PrintResult:
        """Renders a document to PDF."""

        render_pass = render_pass or Pass()
        html = await asyncio.to_thread(self.prepare, document, render_pass)
        path = f"{document.url}?mkdocs-exporter={render_pass.name}"
        url = self.server.publish(path, html)

        try:
            result = await self.browser.print(url, tagged=render_pass.name == "default")
        finally:
            self.server.unpublish(path)

        if self.options.links is None:
            directory = render_pass.directory
            result.pdf = relativize_links(
                result.pdf, document.directory if directory is None else directory
            )

        return result

    async def render_all(
        self, documents: Sequence[Document], passes: Sequence[Pass] | None = None
    ) -> list[Outcome]:
        """Renders documents concurrently; a failing document doesn't stop the others."""

        semaphore = asyncio.Semaphore(max(1, self.options.concurrency))

        async def render(document: Document, render_pass: Pass | None) -> Outcome:
            async with semaphore:
                logger.info("[mkdocs-exporter.pdf] Rendering '%s'...", document.id)

                try:
                    result = await self.render(document, render_pass)
                except RenderError as error:
                    return Outcome(document=document, error=error)

                self._report(document, result)

                return Outcome(document=document, result=result)

        return list(
            await asyncio.gather(
                *(
                    render(document, passes[index] if passes else None)
                    for index, document in enumerate(documents)
                )
            )
        )

    def _report(self, document: Document, result: PrintResult) -> None:
        """Logs what looked suspicious while rendering a document."""

        diagnostics = result.diagnostics

        for error in diagnostics.hook_errors:
            logger.warning(
                "[mkdocs-exporter.pdf] Error in '%s': %s", document.id, error
            )
        for request in diagnostics.failed_requests:
            logger.warning(
                "[mkdocs-exporter.pdf] Failed to load a resource of '%s': %s",
                document.id,
                request,
            )
        for message in [
            *diagnostics.errors,
            *diagnostics.late_errors,
            *diagnostics.console,
            *diagnostics.external_failed_requests,
        ]:
            logger.debug("[mkdocs-exporter.pdf] '%s': %s", document.id, message)
