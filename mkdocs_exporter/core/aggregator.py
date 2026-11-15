from __future__ import annotations

import io
import json
import posixpath
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    Fit,
    FloatObject,
    NameObject,
    NullObject,
    TextStringObject,
)

from mkdocs_exporter.core import book, margins, toc
from mkdocs_exporter.core.browser import RenderError
from mkdocs_exporter.core.css import PageMargin, top_margin
from mkdocs_exporter.core.document import Document, Heading, Position
from mkdocs_exporter.core.html import HtmlDocument
from mkdocs_exporter.core.pdf import RELATIVE_LINKS_BASE, fix_uri, info, link_actions
from mkdocs_exporter.core.server import RESERVED
from mkdocs_exporter.core.toc import TocEntry, TocOptions
from mkdocs_exporter.logging import logger

if TYPE_CHECKING:
    from mkdocs_exporter.core.renderer import Outcome, Renderer

COVER_MODES = ("all", "none", "limits", "book", "front", "back")
"""How cover pages are handled when aggregating documents."""

START_MODES = ("any", "odd")
"""On which pages documents start in an aggregated document."""

POINTS_PER_PIXEL = 0.75
"""PDF points (1/72 in) per CSS pixel (1/96 in)."""

ATTEMPTS = 3
"""How many times a book may be patched and printed again (see `aggregate`)."""


def kept_covers(mode: str, index: int, count: int) -> set[str]:
    """The covers kept for the document at `index` among `count` aggregated documents.

    - `all`: every cover;
    - `none`: no cover;
    - `front` / `back`: every front (resp. back) cover;
    - `limits`: the first document's front cover and the last document's back cover;
    - `book`: every front cover and the last document's back cover.
    """

    if mode == "all":
        return {"front", "back"}
    if mode == "none":
        return set()
    if mode in ("front", "back"):
        return {mode}
    if count == 1:
        return {"front", "back"}
    if mode == "limits":
        return {"front"} if index == 0 else {"back"} if index == count - 1 else set()
    if mode == "book":
        return {"front", "back"} if index == count - 1 else {"front"}

    raise ValueError(f"Unknown cover mode: {mode}")


@dataclass
class NavNode:
    """An entry of the navigation: a section or a document."""

    title: str
    document: str | None = None
    """The identifier of the document (`None` for sections)."""

    children: list[NavNode] = field(default_factory=list)


@dataclass
class Aggregation:
    """A document combining several documents."""

    output: str
    """The location of the combined document, relative to the website's root."""

    documents: Sequence[Document]
    """The documents to combine, in order."""

    covers: str = "all"
    """How cover pages are handled (see `kept_covers`)."""

    start: str = "any"
    """`odd` to start every document on an odd (right-hand) page, adding blank pages."""

    metadata: Mapping[str, object] = field(default_factory=dict)
    """The document information (title, author...)."""

    nav: Sequence[NavNode] | None = None
    """The navigation, used for bookmarks and the table of contents (flat by default)."""

    outline: int = 3
    """The depth of bookmarks: 0 for none, 1 for documents, 2 to add `h2` headings..."""

    toc: TocOptions | None = None
    """The table of contents, inserted after the first document's front cover."""


def metadata(values: Mapping[str, object]) -> dict[str, str]:
    """Normalizes document information keys (`title` → `/Title`)."""

    return info(values)


def flat_nav(documents: Sequence[Document]) -> list[NavNode]:
    """A navigation listing documents."""

    return [
        NavNode(title=document.title, document=document.id) for document in documents
    ]


# --- Measurements ----------------------------------------------------------------------


@dataclass
class MeasuredPart:
    """A part, as printed: its pages (0-based, inclusive) and its headings."""

    id: str
    first: int
    last: int
    front: tuple[int, int] | None = None
    """The pages of its front cover."""

    back: tuple[int, int] | None = None
    """The pages of its back cover."""

    headings: list[Heading] = field(default_factory=list)

    @property
    def pages(self) -> int:
        """Its number of pages."""

        return self.last - self.first + 1


def _span(value: Any) -> tuple[int, int] | None:
    return (int(value[0]), int(value[1])) if value else None


@dataclass
class Measure:
    """The layout of a printed book, as measured by `book.js`."""

    pages: int
    parts: list[MeasuredPart] = field(default_factory=list)
    toc: tuple[int, int] | None = None
    """The pages of the table of contents."""

    blanks: list[int] = field(default_factory=list)
    """The blank pages."""

    rules: list[PageMargin] = field(default_factory=list)
    """The `@page` rules setting a top margin, in order."""

    width: float = 0.0
    """The width of the layout (wider than pages when the browser shrinks them)."""

    @classmethod
    def parse(cls, data: Mapping[str, Any] | None) -> Measure:
        """Reads the measurement of `book.js`."""

        if not data or "error" in data:
            raise ValueError(
                f"The book could not be measured: {(data or {}).get('error')}"
            )

        return cls(
            pages=int(data["pages"]),
            parts=[
                MeasuredPart(
                    id=str(part["id"]),
                    first=int(part["span"][0]),
                    last=int(part["span"][1]),
                    front=_span(part.get("front")),
                    back=_span(part.get("back")),
                    headings=[
                        Heading(
                            level=int(heading["level"]),
                            id=str(heading.get("id") or ""),
                            title=str(heading["title"]),
                            position=Position(
                                int(heading["page"]),
                                float(heading["top"]) * POINTS_PER_PIXEL,
                            ),
                        )
                        for heading in part["headings"]
                    ],
                )
                for part in data["parts"]
                if part.get("span")
            ],
            toc=_span(data.get("toc")),
            blanks=[int(blank[0]) for blank in data.get("blanks") or []],
            rules=[
                PageMargin(
                    str(rule.get("selector", "")), str(rule.get("marginTop", ""))
                )
                for rule in data.get("pageRules") or []
            ],
            width=float(data.get("width") or 0),
        )

    def content(self, part: MeasuredPart) -> range:
        """The pages of a part's content (without covers nor table of contents)."""

        first = part.front[1] + 1 if part.front else part.first
        last = part.back[0] - 1 if part.back else part.last

        if self.toc and part.first <= self.toc[0] <= part.last:
            first = max(first, self.toc[1] + 1)

        return range(first, max(first, last + 1))

    def anchors(self) -> dict[str, Position]:
        """The position of headings, and of the content of each part (by identifier)."""

        positions: dict[str, Position] = {}

        for part in self.parts:
            pages = self.content(part)
            positions[part.id] = Position(min(pages.start, part.last))

            for heading in part.headings:
                if heading.id and heading.position is not None:
                    positions.setdefault(heading.id, heading.position)

        return positions


@dataclass
class Plan:
    """Blank pages making parts start on odd pages."""

    blanks: list[str] = field(default_factory=list)
    """The parts preceded by a blank page."""

    shifts: dict[str, int] = field(default_factory=dict)
    """How many pages each part moves, compared with the measured print."""

    pages: int = 0
    """The number of pages of the book."""


def plan(measure: Measure, start: str = "any") -> Plan:
    """Plans the blank pages of a book (`start: odd`).

    Parts start on a new page of their own: their length doesn't depend on where they
    start, so the measured lengths (blank pages left out) are final.
    """

    result = Plan()
    page = 1

    for part in measure.parts:
        blank = start == "odd" and page % 2 == 0

        if blank:
            result.blanks.append(part.id)

        first = page + blank
        result.shifts[part.id] = first - 1 - part.first
        page = first + part.pages

    result.pages = page - 1

    return result


def running_heads(measure: Measure, plan: Plan) -> list[str]:
    """The `{section}` of each page: its first `h1`/`h2`, or the last one of the part's
    previous pages (nothing on covers, the table of contents and blank pages)."""

    sections = [""] * plan.pages

    for part in measure.parts:
        shift = plan.shifts.get(part.id, 0)
        heads = margins.running_heads(
            (
                (heading.position.page, heading.title)
                for heading in part.headings
                if heading.level <= 2 and heading.position is not None
            ),
            measure.content(part),
        )

        for page, head in heads.items():
            if 0 <= page + shift < len(sections):
                sections[page + shift] = head

    return sections


def _first(node: NavNode, parts: Mapping[str, book.Part]) -> book.Part | None:
    """The first part of a navigation entry."""

    if node.document is not None:
        return parts.get(node.document)

    for child in node.children:
        if (part := _first(child, parts)) is not None:
            return part

    return None


def toc_entries(
    nav: Sequence[NavNode],
    parts: Mapping[str, book.Part],
    page: Callable[[str], int | None],
    depth: int,
) -> list[TocEntry]:
    """The entries of the table of contents.

    Args:
        nav: The navigation.
        parts: The parts, by document identifier.
        page: The page number of an identifier (of a heading or a part).
        depth: The depth of the entries.
    """

    def entries(nodes: Sequence[NavNode]) -> list[TocEntry]:
        result = []

        for node in nodes:
            part = _first(node, parts)

            if part is None:
                continue

            # Headings that aren't printed (e.g. hidden) lead to the part itself.
            anchor = part.anchor if page(part.anchor) is not None else part.id
            entry = TocEntry(
                title=node.title or part.document.title,
                page=page(anchor) or 0,
                href="#" + anchor,
            )

            if node.document is None:
                entry.children = entries(node.children)
            else:
                entry.children = toc.heading_entries(
                    toc.subheadings(part.headings), page, depth
                )

            result.append(entry)

        return result

    return entries(nav)


def outline(
    writer: PdfWriter,
    nav: Sequence[NavNode],
    parts: Mapping[str, book.Part],
    destination: Callable[[str], tuple[int, float] | None],
    depth: int,
) -> None:
    """Adds bookmarks: sections, parts and their headings.

    Args:
        writer: The document.
        nav: The navigation.
        parts: The parts, by document identifier.
        destination: The page index and top (in points) of an identifier.
        depth: The depth of bookmarks.
    """

    if depth < 1:
        return

    def add(nodes: Sequence[NavNode], parent: Any) -> None:
        for node in nodes:
            part = _first(node, parts)
            target = (
                destination(part.anchor) or destination(part.id)
                if part is not None
                else None
            )

            if part is None or target is None:
                continue

            item = writer.add_outline_item(
                title=node.title or part.document.title,
                page_number=target[0],
                parent=parent,
                fit=Fit.xyz(left=0, top=target[1]),
            )

            if node.document is None:
                add(node.children, item)
                continue

            items: dict[int, Any] = {}

            for index, heading, parent_index in toc.nested(
                toc.subheadings(part.headings), depth
            ):
                if (position := destination(heading.id)) is None:
                    continue

                items[index] = writer.add_outline_item(
                    title=heading.title,
                    page_number=position[0],
                    parent=items.get(parent_index, item),
                    fit=Fit.xyz(left=0, top=position[1]),
                    is_open=False,
                )

    add(nav, None)


def lower_destinations(writer: PdfWriter, margins: Sequence[float]) -> None:
    """Lowers named destinations by the top margin (in points) of their page.

    Chromium positions destinations as if pages had no top margin: links would show the
    lines above their target.
    """

    pages = {
        getattr(page.indirect_reference, "idnum", None): index
        for index, page in enumerate(writer.pages)
    }

    def lower(destination: Any) -> None:
        destination = destination.get_object()

        if isinstance(destination, DictionaryObject):
            destination = destination.get("/D")
            destination = destination.get_object() if destination is not None else None
        if (
            not isinstance(destination, ArrayObject)
            or len(destination) < 4
            or destination[1] != "/XYZ"
            or isinstance(destination[3], NullObject)
        ):
            return

        index = pages.get(getattr(destination[0], "idnum", None))

        if index is not None and index < len(margins):
            destination[3] = FloatObject(float(destination[3]) - margins[index])

    def walk(node: Any) -> None:
        node = node.get_object()

        for kid in node.get("/Kids", []):
            walk(kid)

        values = node.get("/Names", [])

        for index in range(1, len(values), 2):
            lower(values[index])

    root: Any = writer.root_object

    if "/Dests" in root:
        for value in root["/Dests"].get_object().values():
            lower(value)
    if "/Names" in root and "/Dests" in root["/Names"].get_object():
        walk(root["/Names"].get_object()["/Dests"])


# --- Aggregation -----------------------------------------------------------------------


def _language(html: str) -> str | None:
    """The language of an HTML document (`<html lang="...">`)."""

    match = re.search(r"<html\b[^>]*\blang=[\"']?([\w-]+)", html[:2048], re.IGNORECASE)

    return match.group(1) if match else None


async def aggregate(
    renderer: Renderer, aggregation: Aggregation, name: str = "aggregate"
) -> list[Outcome]:
    """Prints the documents of an aggregation as a single document.

    Returns:
        The failure, if any (the aggregated document is then not written).
    """

    from mkdocs_exporter.core.renderer import Outcome

    documents = list(aggregation.documents)

    if not documents:
        return []

    site, theme, options = renderer.site, renderer.theme, renderer.options
    output = aggregation.output.lstrip("/")
    directory = posixpath.dirname(output)
    nav = aggregation.nav if aggregation.nav is not None else flat_nav(documents)
    document = Document(id=output, url=documents[0].url, path=output, title=output)

    logger.info("[mkdocs-exporter.pdf] Aggregating pages to '%s'...", output)

    parts = []

    for index, page in enumerate(documents):
        covers = kept_covers(aggregation.covers, index, len(documents)) & set(
            page.covers
        )
        prepared = renderer.prepared.pop(page.id, None)

        if prepared is not None and index > 0:
            # The content prepared for the page's own document (the first page is
            # parsed again: its whole document is the book's shell).
            parts.append(book.reuse(index, page, covers, prepared))
            continue

        html = HtmlDocument(page.html)
        parts.append(
            book.Part(
                index=index,
                document=page,
                covers=covers,
                html=html,
                content=book.part_element(html, theme.content_element(html)),
            )
        )

    settings = book.BookOptions(
        prefix=site.prefix,
        links=options.links or RELATIVE_LINKS_BASE,
        removed=theme.removed,
        hidden=[*theme.hidden, *options.hidden],
        head=[
            f"<script>window.__MKDOCS_EXPORTER__ = "
            f"{json.dumps({'delay': options.delay})};</script>",
            f'<script src="{RESERVED}pdf.js"></script>',
            f'<script src="{RESERVED}book.js"></script>',
            *(
                [f"<script>{script}</script>"]
                if (script := theme.print_script())
                else []
            ),
        ],
        scripts=options.scripts,
        margins=options.margins,
        variables=options.variables,
        base_stylesheets=renderer.base_stylesheets,
        stylesheets=options.stylesheets,
        toc_title=aggregation.toc.title if aggregation.toc else "",
    )

    def prepare(part: book.Part) -> None:
        if part.html is not None:
            renderer.prepare_content(
                part.html, part.content, part.document, part.covers
            )

    book.prepare(parts, settings, prepare)

    by_document = {part.document.id: part for part in parts}
    contents = aggregation.toc

    def render(page: Callable[[str], int | None]) -> str | None:
        if contents is None:
            return None

        return toc.render(contents, toc_entries(nav, by_document, page, contents.depth))

    assembled = book.assemble(parts, settings, render(lambda _: 0))
    sections = options.margins.uses("section")
    applied: dict[str, Any] = {}
    attempts = 0

    def patch(measure: Measure) -> tuple[dict[str, Any], Plan]:
        """What the document needs from a measured print."""

        blank_plan = plan(measure, aggregation.start)
        anchors = measure.anchors()
        starts = sorted((p.first, p.id) for p in measure.parts)

        def number(id: str) -> int | None:
            position = anchors.get(id)

            if position is None:
                return None

            part = next(
                (p for first, p in reversed(starts) if first <= position.page), None
            )

            return position.page + blank_plan.shifts.get(part or "", 0) + 1

        result: dict[str, Any] = {"blanks": blank_plan.blanks}

        if sections:
            result["css"] = margins.sections(running_heads(measure, blank_plan))
        if (html := render(number)) is not None:
            result["toc"] = html

        return result, blank_plan

    async def refine(printed: Any) -> str | None:
        nonlocal attempts, applied

        try:
            computed, _ = patch(Measure.parse(printed.measure))
        except ValueError as error:
            logger.warning("[mkdocs-exporter.pdf] %s ('%s')", error, output)
            return None

        attempts += 1

        if computed == applied and not printed.draft:
            return None
        if attempts >= ATTEMPTS:
            # The document is printed once more, without being checked.
            logger.warning(
                "[mkdocs-exporter.pdf] The page numbering of '%s' did not stabilize, "
                "page numbers may be inaccurate",
                output,
            )

        applied = computed

        return f"window.__MKDOCS_EXPORTER_BOOK__.apply({json.dumps(computed)})"

    needs_patch = contents is not None or aggregation.start == "odd" or sections
    path = f"{documents[0].url}?mkdocs-exporter={name}"
    url = renderer.server.publish(path, assembled.html)

    try:
        result = await renderer.browser.print(
            url,
            outline=False,
            tagged=False,
            refine=refine if needs_patch else None,
            draft=True,
            attempts=ATTEMPTS,
            measure=True,
        )
    except RenderError as error:
        return [Outcome(document=document, error=error)]
    finally:
        renderer.server.unpublish(path)

    renderer.report(document, result)

    try:
        measure = Measure.parse(result.measure)
    except ValueError as error:
        logger.warning("[mkdocs-exporter.pdf] %s ('%s')", error, output)
        measure = Measure(pages=0)

    pdf = finish(
        result.pdf,
        measure,
        assembled,
        nav,
        by_document,
        aggregation,
        lambda uri: fix_uri(
            uri,
            renderer.server.origin,
            site.prefix,
            options.links or RELATIVE_LINKS_BASE,
            directory if options.links is None else None,
        ),
        _language(documents[0].html),
    )
    target = site.directory / output

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pdf)

    return []


def page_names(measure: Measure, names: book.PageNames) -> list[str | None]:
    """The named page of each page of a printed book."""

    result: list[str | None] = [None] * measure.pages

    def mark(pages: Iterator[int] | range, name: str | None) -> None:
        for page in pages:
            if 0 <= page < len(result):
                result[page] = name

    for part in measure.parts:
        mark(range(part.first, part.last + 1), names.content.get(part.id))

        if part.front:
            mark(range(part.front[0], part.front[1] + 1), names.front.get(part.id))
        if part.back:
            mark(range(part.back[0], part.back[1] + 1), book.BACK_COVER_PAGE)

    if measure.toc:
        mark(range(measure.toc[0], measure.toc[1] + 1), book.TOC_PAGE)

    mark(iter(measure.blanks), book.BLANK_PAGE)

    return result


def finish(
    pdf: bytes,
    measure: Measure,
    assembled: book.Book,
    nav: Sequence[NavNode],
    parts: Mapping[str, book.Part],
    aggregation: Aggregation,
    rewrite: Callable[[str], str | None],
    language: str | None,
) -> bytes:
    """Post-processes a printed book: links, destinations, bookmarks, information."""

    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    heights = [float(page.mediabox.height) for page in writer.pages]
    names = page_names(measure, assembled.pages)
    tops = [
        top_margin(measure.rules, name, first=index == 0, right=index % 2 == 0)
        * POINTS_PER_PIXEL
        for index, name in enumerate(names)
    ]
    anchors = measure.anchors() if len(heights) == measure.pages else {}

    if len(heights) != measure.pages:
        logger.warning(
            "[mkdocs-exporter.pdf] The layout of '%s' could not be fully measured (e.g."
            " by Chromium older than 138): page numbers and bookmarks may be inaccurate",
            aggregation.output,
        )

    def destination(id: str) -> tuple[int, float] | None:
        position = anchors.get(id)

        if position is None:
            return None

        top = heights[position.page] - tops[position.page]

        return position.page, max(0.0, top - position.top)

    for _, annotation, uri in link_actions(writer):
        target = rewrite(uri)

        if target is not None and target != uri:
            action = cast(DictionaryObject, annotation["/A"].get_object())
            action[NameObject("/URI")] = TextStringObject(target)

    if len(tops) == len(heights):
        lower_destinations(writer, tops)

    outline(writer, nav, parts, destination, aggregation.outline)

    if language:
        writer.root_object[NameObject("/Lang")] = TextStringObject(language)

    writer.add_metadata(
        {"/Producer": "MkDocs Exporter", **metadata(aggregation.metadata)}
    )

    output = io.BytesIO()

    writer.write(output)

    return output.getvalue()
