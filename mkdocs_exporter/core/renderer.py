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
from mkdocs_exporter.core.browser import Browser, Printed, PrintResult, RenderError
from mkdocs_exporter.core.cache import Assets, Cache, digest, environment, fingerprint
from mkdocs_exporter.core.document import Document, Heading, Layout, Site
from mkdocs_exporter.core.html import (
    ANCESTOR,
    HtmlDocument,
    PageResources,
    page_resources,
    resolve_link,
    teleported,
)
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


def default_concurrency() -> int:
    """The number of documents rendered at once by default.

    Rendering mostly waits for the browser: twice the number of CPUs available to the
    process renders fastest on small machines. Beyond 8, documents render barely faster
    (6 % at 16 on 28 CPUs) for much more memory (the browser peaked at 1.4 GiB with 8
    documents at a time, 2.4 GiB with 16).
    """

    if hasattr(os, "sched_getaffinity"):
        cpus = len(os.sched_getaffinity(0))
    else:
        cpus = os.cpu_count() or 1

    return min(2 * cpus, 8)


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


@dataclass
class Outcome:
    """The outcome of rendering a document."""

    document: Document
    result: PrintResult | None = None
    error: RenderError | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class Prepared:
    """A page's content prepared for its own document, reused as a part of books.

    It spares books another parse of the page: the content is detached from the page's
    document once that document is printed, links resolved (see `rewrite_urls`'s
    `base`) and every cover inserted.
    """

    content: Tag
    resources: PageResources
    teleported: list[tuple[str, str, Tag]] = field(default_factory=list)
    """The elements the content teleports: (origin, destination, element), the origin
    being the location of the cover holding the element (`front`, `back`) or `content`."""


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
        from mkdocs_exporter.core.resources import css

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
        self.base_stylesheets = [
            importlib.resources.files(css).joinpath("base.css").read_text("utf-8"),
            theme.print_stylesheet(),
        ]
        self._assets: Assets = {}

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

    async def render(self, document: Document) -> PrintResult:
        """Renders a document to PDF (or reuses it from the cache)."""

        key = self._key(document) if self.cache else ""

        if self.cache and (result := self.cache.get(key, self._fresh)):
            logger.debug("[mkdocs-exporter.pdf] Reusing '%s'", document.id)
            self.reused += 1

            return result

        logger.info("[mkdocs-exporter.pdf] Rendering '%s'...", document.id)

        # A few milliseconds of CPU: a thread would mostly wait for the GIL (measured
        # about 5 times slower with 4 documents rendered concurrently).
        html, headings = self.prepare(document)
        result = await self._print(document, html, headings)

        self._finish(result, document, headings)

        # Results that may be incomplete are not kept (e.g. a script failed to load).
        if self.cache and result.diagnostics.complete:
            assets = {_path(url): self._asset(url) for url in result.resources}
            self.cache.put(key, result, assets)

        return result

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

    def prepare_content(
        self, html: HtmlDocument, content: Tag, document: Document, covers: set[str]
    ) -> None:
        """Prepares a page's content for printing (also as part of a book).

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
        """The HTML to print for a document, and its headings (outside of covers)."""

        html = HtmlDocument(document.html)
        content = self.theme.content_element(html)

        self.prepare_content(html, content, document, set(document.covers))
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
        contents = _insert_toc(html, content, headings, document.toc)

        _insert_anchors(html, headings)
        self._style(html, document)
        self._script(html)
        html.rewrite_links(
            lambda href: resolve_link(href, document.url, self.site.prefix, self._base)
        )

        output = str(html)

        if resources is not None:
            # Books reuse the content (without what they print themselves) instead of
            # parsing the page again.
            for _, _, element in moved:
                element.extract()
            if contents is not None:
                contents.extract()

            self.prepared[document.id] = Prepared(
                content=content.extract(), resources=resources, teleported=moved
            )

        return output, headings

    @property
    def _base(self) -> str:
        """The URL links to the website start with, once resolved."""

        return self.options.links or RELATIVE_LINKS_BASE

    def _style(self, html: HtmlDocument, document: Document) -> None:
        """Adds the stylesheets of the exporter, the theme, headers and footers and the
        user to a document, then the styles teleported to the head (e.g. by covers),
        which take precedence over them."""

        hidden = [*self.theme.hidden, *self.options.hidden]
        stylesheets = [
            *self.base_stylesheets,
            self.options.margins.stylesheet(
                {**self.options.variables, "page_title": document.title},
                front_cover="front" in document.covers,
            ),
            *self.options.stylesheets,
        ]

        for stylesheet in stylesheets:
            if stylesheet:
                html.add_style(stylesheet)

        if hidden:
            html.add_style(", ".join(hidden) + " { display: none !important; }")

        html.teleport()

    def _script(self, html: HtmlDocument) -> None:
        """Adds the scripts of the exporter, the theme and the user to a document.

        The exporter's are the first scripts of the head (inserted in reverse order),
        so that errors are recorded from the start; the user's are the last of the body.
        """

        if theme_script := self.theme.print_script():
            html.add_script(theme_script, head=True, first=True)

        html.add_script(src=RESERVED + "pdf.js", head=True, first=True)
        html.add_data(
            "__MKDOCS_EXPORTER__", {"delay": self.options.delay}, head=True, first=True
        )

        for script in self.options.scripts:
            html.add_script(script)

    async def _print(
        self, document: Document, html: str, headings: Sequence[Heading]
    ) -> PrintResult:
        """Prints a document's HTML, refined from a first print when needed."""

        path = f"{document.url}?mkdocs-exporter=default"
        url = self.server.publish(path, html)
        refinement = Refinement(self, headings, document.toc)

        try:
            return await self.browser.print(
                url,
                refine=refinement if refinement.needed else None,
                attempts=refinement.attempts,
            )
        finally:
            self.server.unpublish(path)

    def _finish(
        self, result: PrintResult, document: Document, headings: Sequence[Heading]
    ) -> None:
        """Reads the layout of a printed document, and fixes its links and information."""

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
        result.pdf = set_metadata(
            self._rewrite_links(result.pdf, document),
            {
                "creator": "MkDocs Exporter",
                "title": document.title,
                **document.metadata,
            },
        )

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
                self._base,
                document.directory if relativize else None,
            ),
        )

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


class Refinement:
    """Completes a printed document with what browsers can't print by themselves.

    Browsers can't print running heads (`string-set`) nor the page numbers of links'
    targets (`target-counter()`): the document is printed once to find out where its
    headings land, then printed again with the section of every page and the page
    numbers of its table of contents, until they are stable.
    """

    def __init__(
        self,
        renderer: Renderer,
        headings: Sequence[Heading],
        contents: TocOptions | None,
    ) -> None:
        self.renderer = renderer
        self.headings = headings
        self.contents = contents
        self.sections = renderer.options.margins.uses("section")
        """Do headers or footers show the section of pages?"""
        self.listed = bool(_toc_entries(contents, headings, lambda _: 0))
        """Does the document have a table of contents?"""
        self.applied: dict[str, str] = {}

    @property
    def needed(self) -> bool:
        """Does the document need to be refined?"""

        return self.sections or self.listed

    @property
    def attempts(self) -> int:
        """The number of prints refining the document, at most."""

        return 2 if self.listed else 1

    async def __call__(self, printed: Printed) -> str | None:
        """The script updating a printed document (`None` once it is stable)."""

        layout = read_layout(printed.pdf)
        patch = {}

        if self.sections:
            heads = margins.running_heads(
                (
                    (layout.anchors[heading.id].page, heading.title)
                    for heading in self.headings
                    if heading.level <= 2 and heading.id in layout.anchors
                ),
                range(layout.pages),
            )
            patch["css"] = margins.sections(list(heads.values()))
        if self.listed and self.contents is not None:
            entries = _toc_entries(
                self.contents,
                self.headings,
                lambda id: (
                    layout.anchors[id].page + 1 if id in layout.anchors else None
                ),
            )
            patch["toc"] = toc.render(self.contents, entries)
        if patch == self.applied:
            return None

        self.applied = patch

        return f"window.__MKDOCS_EXPORTER_PATCH__({json.dumps(patch)})"


def _toc_entries(
    options: TocOptions | None,
    headings: Sequence[Heading],
    page: Callable[[str], int | None],
) -> list[toc.TocEntry]:
    """The entries of a document's table of contents (none without one)."""

    if options is None:
        return []

    return toc.heading_entries(toc.subheadings(headings), page, options.depth)


def _insert_toc(
    html: HtmlDocument,
    content: Tag,
    headings: Sequence[Heading],
    options: TocOptions | None,
) -> Tag | None:
    """Inserts a document's table of contents after its front cover, with
    placeholder page numbers (filled once printed, see `Refinement`)."""

    entries = _toc_entries(options, headings, lambda _: 0)

    if options is None or not entries:
        return None

    return toc.insert(html, content, toc.render(options, entries))


def _insert_anchors(html: HtmlDocument, headings: Sequence[Heading]) -> None:
    """Inserts hidden links to every heading: browsers create named destinations for
    them, telling where headings land (and letting PDF readers link to them)."""

    if not headings:
        return

    anchors = html.soup.new_tag(
        "nav", attrs={"class": "mkdocs-exporter-anchors", "hidden": ""}
    )

    for heading in headings:
        anchors.append(html.soup.new_tag("a", attrs={"href": f"#{heading.id}"}))

    html.body.append(anchors)


def _path(url: str) -> str:
    """The path and query of a URL."""

    return urlsplit(url)._replace(scheme="", netloc="").geturl()
