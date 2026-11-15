from __future__ import annotations

import io
import json
import posixpath
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

from mkdocs_exporter.core import margins, toc
from mkdocs_exporter.core.books.assembly import (
    Assembly,
    AssemblyOptions,
    Part,
    assemble,
    part_element,
    prepare,
    reuse,
)
from mkdocs_exporter.core.books.layout import (
    POINTS_PER_PIXEL,
    Measure,
    Plan,
    kept_covers,
    page_names,
    plan,
    running_heads,
)
from mkdocs_exporter.core.books.outline import (
    NavNode,
    flat_nav,
    lower_destinations,
    outline,
    toc_entries,
)
from mkdocs_exporter.core.browser import Printed, PrintResult, RenderError
from mkdocs_exporter.core.css import top_margin
from mkdocs_exporter.core.document import Document
from mkdocs_exporter.core.html import HtmlDocument
from mkdocs_exporter.core.pdf import RELATIVE_LINKS_BASE, fix_uri, info, link_actions
from mkdocs_exporter.core.server import RESERVED
from mkdocs_exporter.core.toc import TocOptions
from mkdocs_exporter.logging import logger

if TYPE_CHECKING:
    from mkdocs_exporter.core.renderer import Outcome, Renderer

ATTEMPTS = 3
"""How many times a book may be patched and printed again."""


@dataclass
class Book:
    """Pages combined into a single document."""

    output: str
    """The location of the document, relative to the website's root."""

    documents: Sequence[Document]
    """The pages, in order."""

    covers: str = "all"
    """The cover pages kept (see `kept_covers`)."""

    start: str = "any"
    """`odd` to start every page on an odd (right-hand) page, adding blank pages."""

    metadata: Mapping[str, object] = field(default_factory=dict)
    """The document information (title, author...)."""

    nav: Sequence[NavNode] | None = None
    """The navigation, giving bookmarks and the table of contents (flat by default)."""

    outline: int = 3
    """The depth of bookmarks: 0 for none, 1 for pages, 2 to add `h2` headings..."""

    toc: TocOptions | None = None
    """The table of contents, inserted after the first page's front cover."""


async def print_book(
    renderer: Renderer, book: Book, name: str = "book"
) -> list[Outcome]:
    """Prints a book and writes it (see `BookPrinter`)."""

    return await BookPrinter(renderer, book, name).print()


class BookPrinter:
    """Prints a book: its pages assembled in a single HTML document, printed once.

    What browsers can't print natively is computed from a first print (a draft: the
    whole document is laid out, only its first page printed), measured by `book.js`:
    page numbers of the table of contents, blank pages making pages start on odd pages,
    running heads (`{section}`). The document is patched and printed again; bookmarks
    are then added from the measurement of the final print.
    """

    def __init__(self, renderer: Renderer, book: Book, name: str = "book") -> None:
        self.renderer = renderer
        self.book = book
        self.name = name
        self.output = book.output.lstrip("/")
        self.nav = book.nav if book.nav is not None else flat_nav(book.documents)
        self.parts: dict[str, Part] = {}
        """The parts, by document identifier."""
        self.applied: dict[str, Any] = {}
        """The last patch applied to the document."""
        self.attempts = 0

    async def print(self) -> list[Outcome]:
        """Prints the book and writes it.

        Returns:
            The failure, if any (the book is then not written).
        """

        from mkdocs_exporter.core.renderer import Outcome

        documents = list(self.book.documents)

        if not documents:
            return []

        logger.info("[mkdocs-exporter.pdf] Combining pages into '%s'...", self.output)

        assembly = self._assemble(documents)
        document = Document(
            id=self.output, url=documents[0].url, path=self.output, title=self.output
        )

        try:
            result = await self._print(documents[0].url, assembly.html)
        except RenderError as error:
            return [Outcome(document=document, error=error)]

        self.renderer.report(document, result)

        target = self.renderer.site.directory / self.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self._finish(result, assembly, documents[0].html))

        return []

    def _assemble(self, documents: Sequence[Document]) -> Assembly:
        """Assembles the pages into a single HTML document."""

        parts = [
            self._part(index, document, len(documents))
            for index, document in enumerate(documents)
        ]
        options = self._options()

        prepare(parts, options, self._prepare_content)
        self.parts = {part.document.id: part for part in parts}

        return assemble(parts, options, self._toc(lambda _: 0))

    def _part(self, index: int, document: Document, count: int) -> Part:
        """A page, as a part of the book."""

        covers = kept_covers(self.book.covers, index, count) & set(document.covers)
        prepared = self.renderer.preparer.prepared.pop(document.id, None)

        # The content prepared for the page's own document is reused, except for the
        # first page: its whole document is the book's shell.
        if prepared is not None and index > 0:
            return reuse(index, document, covers, prepared)

        html = HtmlDocument(document.html)
        content = part_element(html, self.renderer.theme.content_element(html))

        return Part(
            index=index, document=document, covers=covers, html=html, content=content
        )

    def _prepare_content(self, part: Part) -> None:
        if part.html is not None:
            self.renderer.preparer.prepare_content(
                part.html, part.content, part.document, part.covers
            )

    def _options(self) -> AssemblyOptions:
        renderer = self.renderer
        theme, options = renderer.theme, renderer.options
        script = theme.print_script()

        return AssemblyOptions(
            prefix=renderer.site.prefix,
            links=options.links or RELATIVE_LINKS_BASE,
            removed=theme.removed,
            hidden=[*theme.hidden, *options.hidden],
            head=[
                f"<script>window.__MKDOCS_EXPORTER__ = "
                f"{json.dumps({'delay': options.delay})};</script>",
                f'<script src="{RESERVED}pdf.js"></script>',
                f'<script src="{RESERVED}book.js"></script>',
                *([f"<script>{script}</script>"] if script else []),
            ],
            scripts=options.scripts,
            margins=options.margins,
            variables=options.variables,
            base_stylesheets=renderer.preparer.base_stylesheets,
            stylesheets=options.stylesheets,
            toc_title=self.book.toc.title if self.book.toc else "",
        )

    def _toc(self, page: Callable[[str], int | None]) -> str | None:
        """The table of contents, with the page numbers of identifiers."""

        if self.book.toc is None:
            return None

        entries = toc_entries(self.nav, self.parts, page, self.book.toc.depth)

        return toc.render(self.book.toc, entries)

    async def _print(self, url: str, html: str) -> PrintResult:
        """Prints the assembled document, patched from measured prints when needed."""

        server = self.renderer.server
        path = f"{url}?mkdocs-exporter={self.name}"
        patched = (
            self.book.toc is not None
            or self.book.start == "odd"
            or self.renderer.options.margins.uses("section")
        )

        try:
            return await self.renderer.browser.print(
                server.publish(path, html),
                outline=False,
                tagged=False,
                refine=self._refine if patched else None,
                draft=True,
                attempts=ATTEMPTS,
                measure=True,
            )
        finally:
            server.unpublish(path)

    async def _refine(self, printed: Printed) -> str | None:
        """The script patching the document after a print (`None` once stable)."""

        try:
            patch, _ = self._patch(Measure.parse(printed.measure))
        except ValueError as error:
            logger.warning("[mkdocs-exporter.pdf] %s ('%s')", error, self.output)
            return None

        self.attempts += 1

        if patch == self.applied and not printed.draft:
            return None
        if self.attempts >= ATTEMPTS:
            # The document is printed once more, without being checked.
            logger.warning(
                "[mkdocs-exporter.pdf] The page numbering of '%s' did not stabilize, "
                "page numbers may be inaccurate",
                self.output,
            )

        self.applied = patch

        return f"window.__MKDOCS_EXPORTER_BOOK__.apply({json.dumps(patch)})"

    def _patch(self, measure: Measure) -> tuple[dict[str, Any], Plan]:
        """What the document needs after a measured print: blank pages, running heads
        and the page numbers of its table of contents."""

        blank_plan = plan(measure, self.book.start)
        anchors = measure.anchors()
        starts = sorted((part.first, part.id) for part in measure.parts)

        def number(id: str) -> int | None:
            position = anchors.get(id)

            if position is None:
                return None

            part = next(
                (p for first, p in reversed(starts) if first <= position.page), None
            )

            return position.page + blank_plan.shifts.get(part or "", 0) + 1

        patch: dict[str, Any] = {"blanks": blank_plan.blanks}

        if self.renderer.options.margins.uses("section"):
            patch["css"] = margins.sections(running_heads(measure, blank_plan))
        if (html := self._toc(number)) is not None:
            patch["toc"] = html

        return patch, blank_plan

    def _finish(self, result: PrintResult, assembly: Assembly, html: str) -> bytes:
        """Post-processes the printed book: links, destinations, bookmarks, information."""

        try:
            measure = Measure.parse(result.measure)
        except ValueError as error:
            logger.warning("[mkdocs-exporter.pdf] %s ('%s')", error, self.output)
            measure = Measure(pages=0)

        writer = PdfWriter(clone_from=PdfReader(io.BytesIO(result.pdf)))
        heights = [float(page.mediabox.height) for page in writer.pages]
        names = page_names(measure, assembly.pages)
        tops = [
            top_margin(measure.rules, name, first=index == 0, right=index % 2 == 0)
            * POINTS_PER_PIXEL
            for index, name in enumerate(names)
        ]
        measured = len(heights) == measure.pages
        anchors = measure.anchors() if measured else {}

        if not measured:
            logger.warning(
                "[mkdocs-exporter.pdf] The layout of '%s' could not be fully measured "
                "(e.g. by Chromium older than 138): page numbers and bookmarks may be "
                "inaccurate",
                self.output,
            )

        def destination(id: str) -> tuple[int, float] | None:
            position = anchors.get(id)

            if position is None:
                return None

            top = heights[position.page] - tops[position.page]

            return position.page, max(0.0, top - position.top)

        self._rewrite_links(writer)

        if len(tops) == len(heights):
            lower_destinations(writer, tops)

        outline(writer, self.nav, self.parts, destination, self.book.outline)

        if language := _language(html):
            writer.root_object[NameObject("/Lang")] = TextStringObject(language)

        writer.add_metadata(
            {"/Producer": "MkDocs Exporter", **info(self.book.metadata)}
        )

        output = io.BytesIO()
        writer.write(output)

        return output.getvalue()

    def _rewrite_links(self, writer: PdfWriter) -> None:
        """Fixes links to the local server and makes links relative when needed."""

        renderer = self.renderer
        links = renderer.options.links

        for _, annotation, uri in link_actions(writer):
            target = fix_uri(
                uri,
                renderer.server.origin,
                renderer.site.prefix,
                links or RELATIVE_LINKS_BASE,
                posixpath.dirname(self.output) if links is None else None,
            )

            if target is not None and target != uri:
                action = cast(DictionaryObject, annotation["/A"].get_object())
                action[NameObject("/URI")] = TextStringObject(target)


def _language(html: str) -> str | None:
    """The language of an HTML document (`<html lang="...">`)."""

    match = re.search(r"<html\b[^>]*\blang=[\"']?([\w-]+)", html[:2048], re.IGNORECASE)

    return match.group(1) if match else None
