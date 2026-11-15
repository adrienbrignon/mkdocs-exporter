from __future__ import annotations

import asyncio
import dataclasses
import json
import os
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from urllib.parse import urlsplit

from mkdocs_exporter.core import margins, toc
from mkdocs_exporter.core.browser import Browser, Printed, PrintResult, RenderError
from mkdocs_exporter.core.cache import Assets, Cache, digest, environment, fingerprint
from mkdocs_exporter.core.document import Document, Heading, Layout, Site
from mkdocs_exporter.core.margins import Margins
from mkdocs_exporter.core.pdf import (
    RELATIVE_LINKS_BASE,
    fix_uri,
    read_layout,
    rewrite_links,
    set_metadata,
)
from mkdocs_exporter.core.preparation import Prepared, Preparer, toc_entries
from mkdocs_exporter.core.server import Server
from mkdocs_exporter.core.themes import Theme
from mkdocs_exporter.core.toc import TocOptions
from mkdocs_exporter.logging import logger


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
class Context:
    """What documents are rendered with: the website and its theme, the browser
    printing them, the server exposing the website to it, and the options."""

    site: Site
    theme: Theme
    browser: Browser
    server: Server
    options: RenderOptions = field(default_factory=RenderOptions)

    @cached_property
    def preparer(self) -> Preparer:
        """Prepares the HTML printed for documents."""

        return Preparer(self.site, self.theme, self.options)


@dataclass
class Outcome:
    """The outcome of rendering a document."""

    document: Document
    result: PrintResult | None = None
    error: RenderError | None = None
    prepared: Prepared | None = None
    """The content prepared for the document, kept for books (see `Prepared`)."""


class Renderer:
    """Renders documents to PDF with a browser, through a server exposing the website."""

    def __init__(self, context: Context, cache: Cache | None = None) -> None:
        self.context = context
        self.cache = cache
        self.reused = 0
        """The number of documents reused from the cache."""
        self._assets: Assets = {}

    async def render_all(
        self, documents: Sequence[Document], keep: Collection[str] = ()
    ) -> list[Outcome]:
        """Renders documents concurrently; a failing document doesn't stop the others.

        Args:
            documents: The documents.
            keep: The identifiers of the documents whose prepared content is kept for
                books (unless they are reused from the cache).
        """

        options = self.context.options
        semaphore = asyncio.Semaphore(options.concurrency or default_concurrency())

        async def render(document: Document) -> Outcome:
            async with semaphore:
                try:
                    result, prepared = await self.render(document, document.id in keep)
                except RenderError as error:
                    return Outcome(document=document, error=error)

                report(document, result)

                return Outcome(document=document, result=result, prepared=prepared)

        return list(await asyncio.gather(*(render(d) for d in documents)))

    async def render(
        self, document: Document, keep: bool = False
    ) -> tuple[PrintResult, Prepared | None]:
        """Renders a document to PDF (or reuses it from the cache), returning its
        prepared content when asked to `keep` it."""

        key = self._key(document) if self.cache else ""

        if self.cache and (result := self.cache.get(key, self._fresh)):
            logger.debug("[mkdocs-exporter.pdf] Reusing '%s'", document.id)
            self.reused += 1

            return result, None

        logger.info("[mkdocs-exporter.pdf] Rendering '%s'...", document.id)

        # A few milliseconds of CPU: a thread would mostly wait for the GIL (measured
        # about 5 times slower with 4 documents rendered concurrently).
        html, headings, prepared = self.context.preparer.prepare(document, keep)
        result = await self._print(document, html, headings)

        self._finish(result, document, headings)

        # Results that may be incomplete are not kept (e.g. a script failed to load).
        if self.cache and result.diagnostics.complete:
            assets = {_path(url): self._asset(url) for url in result.resources}
            self.cache.put(key, result, assets)

        return result, prepared

    async def _print(
        self, document: Document, html: str, headings: Sequence[Heading]
    ) -> PrintResult:
        """Prints a document's HTML, refined from a first print when needed."""

        path = f"{document.url}?mkdocs-exporter=default"
        url = self.context.server.publish(path, html)
        refinement = Refinement(
            headings, document.toc, self.context.options.margins.uses("section")
        )

        try:
            return await self.context.browser.print(
                url,
                refine=refinement if refinement.needed else None,
                attempts=refinement.attempts,
            )
        finally:
            self.context.server.unpublish(path)

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

        origin = self.context.server.origin
        relativize = self.context.options.links is None

        if origin.encode() not in pdf and not (
            relativize and RELATIVE_LINKS_BASE.encode() in pdf
        ):
            return pdf

        return rewrite_links(
            pdf,
            lambda uri: fix_uri(
                uri,
                origin,
                self.context.site.prefix,
                self._base,
                document.directory if relativize else None,
            ),
        )

    @property
    def _base(self) -> str:
        """The URL links to the website start with, once resolved."""

        return self.context.options.links or RELATIVE_LINKS_BASE

    def _key(self, document: Document) -> str:
        """Identifies a document's inputs (besides the resources it loads)."""

        options = dataclasses.asdict(self.context.options)

        del options["concurrency"]

        return fingerprint(
            environment(),
            self.context.browser.version,
            self.context.browser.options,
            self.context.theme.name,
            self.context.site.url,
            self.context.site.prefix,
            options,
            dataclasses.asdict(document),
        )

    def _asset(self, url: str) -> str | None:
        """The fingerprint of a resource served to the browser (`None` if missing)."""

        path = _path(url)

        if path not in self._assets:
            resource = self.context.server.resolve(path)
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
        headings: Sequence[Heading],
        contents: TocOptions | None,
        sections: bool,
    ) -> None:
        self.headings = headings
        self.contents = contents
        self.sections = sections
        """Do headers or footers show the section of pages?"""
        self.listed = bool(toc_entries(contents, headings, lambda _: 0))
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
            entries = toc_entries(
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


def report(document: Document, result: PrintResult) -> None:
    """Logs what looked suspicious while rendering a document."""

    diagnostics = result.diagnostics

    for error in diagnostics.hook_errors:
        logger.warning("[mkdocs-exporter.pdf] Error in '%s': %s", document.id, error)
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
