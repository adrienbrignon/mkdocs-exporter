from __future__ import annotations

import asyncio
import dataclasses
import importlib.resources
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from bs4 import Tag

from mkdocs_exporter.core import margins, toc
from mkdocs_exporter.core.book import Prepared, page_resources, teleported
from mkdocs_exporter.core.browser import Browser, Printed, PrintResult, RenderError
from mkdocs_exporter.core.cache import Assets, Cache, digest, environment, fingerprint
from mkdocs_exporter.core.document import Document, Heading, Layout, Site
from mkdocs_exporter.core.html import ANCESTOR, HtmlDocument, resolve_link
from mkdocs_exporter.core.html import headings as find_headings
from mkdocs_exporter.core.margins import Margins
from mkdocs_exporter.core.pdf import (
    RELATIVE_LINKS_BASE,
    fix_uri,
    read_layout,
    rewrite_links,
    set_metadata,
)
from mkdocs_exporter.core.server import RESERVED, Server
from mkdocs_exporter.core.themes import Theme
from mkdocs_exporter.core.toc import TocOptions
from mkdocs_exporter.logging import logger

COVER_LOCATIONS = ("front", "back")
"""The locations of cover pages."""

PATCH = """(patch) => {
  if (patch.css !== undefined) {
    let style = document.getElementById('mkdocs-exporter-sections');

    if (!style) {
      style = document.createElement('style');
      style.id = 'mkdocs-exporter-sections';
      document.head.appendChild(style);
    }

    style.textContent = patch.css;
  }

  const contents = document.querySelector('.mkdocs-exporter-toc');

  if (patch.toc !== undefined && contents) {
    contents.innerHTML = patch.toc;
  }
}"""
"""Updates a printed document: running heads (`css`), table of contents (`toc`)."""


def default_concurrency() -> int:
    """The number of documents rendered at once by default.

    Rendering mostly waits for the browser: twice the number of CPUs available to the
    process renders fastest on small machines, and more than 16 brings nothing.
    """

    if hasattr(os, "sched_getaffinity"):
        cpus = len(os.sched_getaffinity(0))
    else:
        cpus = os.cpu_count() or 1

    return min(2 * cpus, 16)


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

    concurrency: int | None = None
    """The number of documents rendered at once (see `default_concurrency`)."""

    hidden: Sequence[str] = (".mkdocs-exporter-ignore", ".headerlink")
    """Selectors of elements that must not appear in documents (besides the theme's)."""

    title: bool = False
    """Should the document's title be inserted when its content has no `h1` heading?"""

    margins: Margins = field(default_factory=Margins)
    """Headers and footers."""

    variables: Mapping[str, str] = field(default_factory=dict)
    """Values of the placeholders of headers and footers (e.g. `site_name`)."""

    toc: TocOptions | None = None
    """A table of contents of the document's headings, inserted after its front cover
    (when it has headings besides its title)."""


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
        cache: Cache | None = None,
    ) -> None:
        self.site = site
        self.theme = theme
        self.browser = browser
        self.server = server
        self.options = options or RenderOptions()
        self.cache = cache
        self.reused = 0
        """The number of documents reused from the cache."""
        self.keep: set[str] = set()
        """The documents whose prepared content is kept for books (see `prepared`)."""
        self.prepared: dict[str, Prepared] = {}
        """The content prepared for documents to keep, by identifier."""
        self._assets: Assets = {}

        from mkdocs_exporter.core.resources import css

        self.base_stylesheets = [
            importlib.resources.files(css)
            .joinpath("base.css")
            .read_text(encoding="utf-8"),
            theme.print_stylesheet(),
        ]

    def prepare_content(
        self, html: HtmlDocument, content: Tag, document: Document, covers: set[str]
    ) -> None:
        """Prepares a page's content for printing (also as part of a combined document).

        Inserts the title (when asked to) and cover pages, opens `<details>` and removes
        what must not be printed (permalinks, the theme's `removed` elements).
        """

        if self.options.title and document.title and content.find("h1") is None:
            heading = html.soup.new_tag("h1", attrs={"class": "mkdocs-exporter-title"})
            heading.string = document.title
            content.insert(0, heading)

        for location in COVER_LOCATIONS:
            if location in covers and location in document.covers:
                cover = html.fragment(
                    document.covers[location],
                    **{"class": f"mkdocs-exporter-{location}-cover"},
                )

                if location == "front":
                    content.insert(0, cover)
                else:
                    content.append(cover)

        html.set_attribute("details:not([open])", "open", "")
        html.remove([".headerlink", *self.theme.removed])

    def prepare(self, document: Document) -> tuple[str, list[Heading]]:
        """Returns the HTML to print for a document, and its headings.

        Headings are those outside of covers. Hidden
        links to each of them make the browser create named destinations, which tell
        where headings land (and let PDF readers link to them).
        """

        html = HtmlDocument(document.html)
        hidden = [*self.theme.hidden, *self.options.hidden]
        base = self.options.links or RELATIVE_LINKS_BASE
        kept = set(document.covers)
        content = self.theme.content_element(html)

        self.prepare_content(html, content, document, kept)
        html.mark_ancestors(content, ANCESTOR)

        # Without content element (the whole body), books parse the page again (see
        # `book.part_element`).
        keep = document.id in self.keep and content.name != "body"
        resources = (
            page_resources(html, content, document.url, self.site.prefix)
            if keep
            else None
        )
        moved = teleported(content) if keep else []

        headings = find_headings(content)
        contents = self._insert_toc(html, content, headings)

        if headings:
            anchors = html.soup.new_tag(
                "nav", attrs={"class": "mkdocs-exporter-anchors", "hidden": ""}
            )

            for heading in headings:
                anchors.append(html.soup.new_tag("a", attrs={"href": f"#{heading.id}"}))

            html.body.append(anchors)

        stylesheets = [
            *self.base_stylesheets,
            self.options.margins.stylesheet(
                {**self.options.variables, "page_title": document.title},
                front_cover="front" in kept,
            ),
            *self.options.stylesheets,
        ]

        for stylesheet in stylesheets:
            if stylesheet:
                html.add_style(stylesheet)

        if hidden:
            html.add_style(", ".join(hidden) + " { display: none !important; }")

        # After the stylesheets, so that styles teleported to the head (e.g. by cover
        # pages) take precedence over them.
        html.teleport()

        # Inserted first in the head (hence in reverse order) to run before any script of
        # the website, so that errors are recorded from the start.
        if theme_script := self.theme.print_script():
            html.add_script(theme_script, head=True, first=True)

        html.add_script(src=RESERVED + "pdf.js", head=True, first=True)
        html.add_data(
            "__MKDOCS_EXPORTER__", {"delay": self.options.delay}, head=True, first=True
        )

        for script in self.options.scripts:
            html.add_script(script)

        html.rewrite_links(
            lambda href: resolve_link(href, document.url, self.site.prefix, base)
        )

        output = str(html)

        if resources is not None:
            # Books reuse the content instead of parsing the page again (the rest of
            # the page's document is left to the garbage collector).
            for _, _, element in moved:
                element.extract()

            # Books have a table of contents of their own.
            if contents is not None:
                contents.extract()

            self.prepared[document.id] = Prepared(
                content=content.extract(), resources=resources, teleported=moved
            )

        return output, headings

    def _toc_entries(
        self, headings: Sequence[Heading], page: Callable[[str], int | None]
    ) -> list[toc.TocEntry]:
        """The entries of a document's table of contents (none without the option)."""

        if self.options.toc is None:
            return []

        return toc.heading_entries(
            toc.subheadings(headings), page, self.options.toc.depth
        )

    def _insert_toc(
        self, html: HtmlDocument, content: Tag, headings: Sequence[Heading]
    ) -> Tag | None:
        """Inserts a document's table of contents after its front cover, with
        placeholder page numbers (filled once printed, see `render`)."""

        entries = self._toc_entries(headings, lambda _: 0)

        if self.options.toc is None or not entries:
            return None

        element = html.fragment(
            toc.render(self.options.toc, entries), **{"class": toc.CLASS}
        )
        covers = content.find_all(class_="mkdocs-exporter-front-cover", recursive=False)

        if covers:
            covers[0].insert_after(element)
        else:
            content.insert(0, element)

        return element

    async def render(self, document: Document) -> PrintResult:
        """Renders a document to PDF."""

        cache = self.cache
        key = self._key(document) if cache else ""

        if cache and (result := cache.get(key, self._fresh)):
            logger.debug("[mkdocs-exporter.pdf] Reusing '%s'", document.id)
            self.reused += 1

            return result

        logger.info("[mkdocs-exporter.pdf] Rendering '%s'...", document.id)

        # A few milliseconds of CPU: a thread would mostly wait for the GIL (measured
        # about 5 times slower with 4 documents rendered concurrently).
        html, headings = self.prepare(document)
        path = f"{document.url}?mkdocs-exporter=default"
        url = self.server.publish(path, html)
        refine = None
        sections = self.options.margins.uses("section")
        listed = bool(self._toc_entries(headings, lambda _: 0))

        if sections or listed:
            # The browser can't print running headings (`string-set`) nor the page
            # numbers of links' targets (`target-counter()`): print once to find out
            # where headings land, then print again with the section of every page and
            # the page numbers of the table of contents (until they are stable).
            running = [(h.id, h.title) for h in headings if h.level <= 2]
            applied: dict[str, str] = {}

            async def refine(printed: Printed) -> str | None:
                layout = read_layout(printed.pdf)
                patch = {}

                if sections:
                    heads = margins.running_heads(
                        (
                            (layout.anchors[id].page, title)
                            for id, title in running
                            if id in layout.anchors
                        ),
                        range(layout.pages),
                    )
                    patch["css"] = margins.sections(list(heads.values()))
                if listed and self.options.toc is not None:
                    entries = self._toc_entries(
                        headings,
                        lambda i: (
                            layout.anchors[i].page + 1 if i in layout.anchors else None
                        ),
                    )
                    patch["toc"] = toc.render(self.options.toc, entries)
                if patch == applied:
                    return None

                applied.clear()
                applied.update(patch)

                return f"({PATCH})({json.dumps(patch)})"

        try:
            result = await self.browser.print(
                url, refine=refine, attempts=2 if listed else 1
            )
        finally:
            self.server.unpublish(path)

        layout = read_layout(result.pdf)
        result.layout = Layout(
            pages=layout.pages,
            anchors=layout.anchors,
            headings=[
                dataclasses.replace(heading, position=layout.anchors[heading.id])
                for heading in headings
                if heading.id in layout.anchors
            ],
        )
        result.pdf = self._rewrite_links(result.pdf, document)
        result.pdf = set_metadata(
            result.pdf,
            {
                "creator": "MkDocs Exporter",
                "title": document.title,
                **document.metadata,
            },
        )

        diagnostics = result.diagnostics

        if cache and not (
            diagnostics.hook_errors
            or diagnostics.failed_requests
            or diagnostics.external_failed_requests
        ):
            # Results that may be incomplete are not kept (e.g. a script failed to load).
            cache.put(key, result, {_path(u): self._asset(u) for u in result.resources})

        return result

    def _key(self, document: Document) -> str:
        """Identifies a document's inputs (besides the resources it loads)."""

        options = dataclasses.asdict(self.options)

        del options["concurrency"]

        return fingerprint(
            environment(),
            self.browser.version,
            self.browser.options,
            self.theme.name,
            self.site.url,
            self.site.prefix,
            options,
            dataclasses.asdict(document),
        )

    def _asset(self, url: str) -> str | None:
        """The fingerprint of a resource served to the browser (`None` if missing)."""

        path = _path(url)

        if path not in self._assets:
            resource = self.server.resolve(path)
            self._assets[path] = digest(resource.data if resource else None)

        return self._assets[path]

    def _fresh(self, assets: Assets) -> bool:
        """Are the resources a document loaded unchanged?"""

        return all(self._asset(url) == value for url, value in assets.items())

    def _rewrite_links(self, pdf: bytes, document: Document) -> bytes:
        """Fixes links to the local server and makes links relative when needed."""

        origin = self.server.origin
        relativize = self.options.links is None

        if origin.encode() not in pdf and not (
            relativize and RELATIVE_LINKS_BASE.encode() in pdf
        ):
            return pdf

        return rewrite_links(
            pdf,
            lambda uri: fix_uri(
                uri,
                origin,
                self.site.prefix,
                self.options.links or RELATIVE_LINKS_BASE,
                document.directory if relativize else None,
            ),
        )

    async def render_all(self, documents: Sequence[Document]) -> list[Outcome]:
        """Renders documents concurrently; a failing document doesn't stop the others."""

        semaphore = asyncio.Semaphore(self.options.concurrency or default_concurrency())

        async def render(document: Document) -> Outcome:
            async with semaphore:
                try:
                    result = await self.render(document)
                except RenderError as error:
                    return Outcome(document=document, error=error)

                self.report(document, result)

                return Outcome(document=document, result=result)

        return list(await asyncio.gather(*(render(d) for d in documents)))

    def report(self, document: Document, result: PrintResult) -> None:
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


def _path(url: str) -> str:
    """The path and query of a URL."""

    return urlsplit(url)._replace(scheme="", netloc="").geturl()
