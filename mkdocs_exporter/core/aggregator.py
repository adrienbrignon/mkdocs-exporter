"""Combines documents into a single PDF document (a "book")."""

from __future__ import annotations

import importlib.resources
import io
import posixpath
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, cast

from jinja2 import Environment
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    Fit,
    FloatObject,
    IndirectObject,
    NameObject,
    NullObject,
    TextStringObject,
)

from mkdocs_exporter.core.document import Document, Heading, Layout, Position, Site
from mkdocs_exporter.core.pdf import RELATIVE_LINKS_BASE, link_actions, relative_url
from mkdocs_exporter.logging import logger

if TYPE_CHECKING:
    from pathlib import Path

    from mkdocs_exporter.core.browser import PrintResult
    from mkdocs_exporter.core.renderer import Outcome, Renderer

COVER_MODES = ("all", "none", "limits", "book", "front", "back")
"""How cover pages are handled when aggregating documents."""

START_MODES = ("any", "odd")
"""On which pages documents start in an aggregated document."""

POINTS_PER_PIXEL = 0.75
"""PDF points (1/72 in) per CSS pixel (1/96 in)."""


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
class TocOptions:
    """Options of the table of contents of an aggregated document."""

    title: str = "Table of contents"
    depth: int = 2
    """The depth of the entries: 1 for documents only, 2 to add their `h2` headings..."""

    template: str | None = None
    """A Jinja template replacing the default one."""


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


@dataclass
class Part:
    """A document within the aggregated document."""

    document: Document
    covers: set[str]
    """The covers kept."""

    first_page: int
    """The number of its first page in the aggregated document."""

    pages: int
    """Its (expected) number of pages in the aggregated document."""

    layout: Layout
    """Its (expected) layout in the aggregated document."""

    blank_before: bool = False
    """Is it preceded by a blank page?"""

    def start(self) -> Position:
        """Where its content starts: its title, or the page following its front cover."""

        headings = self.layout.headings

        if headings and headings[0].level == 1:
            return headings[0].position

        covers = (
            self.layout.cover_pages.get("front", 0) if "front" in self.covers else 0
        )

        return Position(page=min(covers, max(0, self.pages - 1)), top=0)


def _number(parts: list[Part], start: str) -> list[Part]:
    """Numbers the pages of the parts (inserting blank pages if needed)."""

    page = 1

    for part in parts:
        part.blank_before = start == "odd" and page % 2 == 0
        part.first_page = page + part.blank_before
        page = part.first_page + part.pages

    return parts


def plan(
    documents: Sequence[Document],
    layouts: Mapping[str, Layout],
    mode: str,
    start: str = "any",
) -> list[Part]:
    """Plans the aggregated document from the layout of each rendered document."""

    parts = []

    for index, document in enumerate(documents):
        layout = layouts[document.id]
        covers = kept_covers(mode, index, len(documents)) & set(document.covers)
        removed = set(document.covers) - covers
        pages = layout.pages - sum(layout.cover_pages.get(c, 0) for c in removed)

        parts.append(
            Part(
                document=document,
                covers=covers,
                first_page=0,
                pages=pages,
                layout=layout,
            )
        )

    return _number(parts, start)


def renumber(
    parts: Sequence[Part], layouts: Sequence[Layout], start: str = "any"
) -> list[Part]:
    """Plans the aggregated document again from the actual layout of each part."""

    return _number(
        [
            replace(part, pages=layout.pages, layout=layout)
            for part, layout in zip(parts, layouts, strict=True)
        ],
        start,
    )


def total_pages(parts: Sequence[Part]) -> int:
    """The number of pages of the aggregated document."""

    return parts[-1].first_page + parts[-1].pages - 1 if parts else 0


def metadata(values: Mapping[str, object]) -> dict[str, str]:
    """Normalizes document information keys (`title` → `/Title`)."""

    result = {}

    for key, value in values.items():
        if value is None:
            continue

        name = key if key.startswith("/") else "/" + key[:1].upper() + key[1:]
        result[name] = str(value)

    return result


def flat_nav(documents: Sequence[Document]) -> list[NavNode]:
    """A navigation listing documents."""

    return [
        NavNode(title=document.title, document=document.id) for document in documents
    ]


def _nested(
    headings: Sequence[Heading], depth: int
) -> Iterator[tuple[int, Heading, int]]:
    """Headings up to a level: (index, heading, index of the parent heading or -1)."""

    stack: list[tuple[int, int]] = []

    for index, heading in enumerate(headings):
        if heading.level > depth:
            continue

        while stack and stack[-1][0] >= heading.level:
            stack.pop()

        yield index, heading, stack[-1][1] if stack else -1
        stack.append((heading.level, index))


def _sub_headings(part: Part) -> list[Heading]:
    """The headings of a part, without its title."""

    headings = part.layout.headings

    return list(headings[1:] if headings and headings[0].level == 1 else headings)


def _first(node: NavNode, parts: Mapping[str, Part]) -> Part | None:
    """The first part of a navigation entry."""

    if node.document is not None:
        return parts.get(node.document)

    for child in node.children:
        if (part := _first(child, parts)) is not None:
            return part

    return None


@dataclass
class TocEntry:
    """An entry of the table of contents."""

    title: str
    page: int
    href: str
    children: list[TocEntry] = field(default_factory=list)


def toc_entries(
    nav: Sequence[NavNode], parts: Sequence[Part], depth: int, prefix: str
) -> list[TocEntry]:
    """The entries of the table of contents (`prefix` is the website's path)."""

    by_id = {part.document.id: part for part in parts}

    def href(part: Part, anchor: str | None = None) -> str:
        return prefix + part.document.url + (f"#{anchor}" if anchor else "")

    def entries(nodes: Sequence[NavNode]) -> list[TocEntry]:
        result = []

        for node in nodes:
            part = _first(node, by_id)

            if part is None:
                continue

            entry = TocEntry(
                title=node.title or part.document.title,
                page=part.first_page + part.start().page,
                href=href(part),
            )

            if node.document is None:
                entry.children = entries(node.children)
            else:
                created: dict[int, TocEntry] = {}

                for index, heading, parent in _nested(_sub_headings(part), depth):
                    child = TocEntry(
                        title=heading.title,
                        page=part.first_page + heading.position.page,
                        href=href(part, heading.id),
                    )
                    created[index] = child
                    siblings = (
                        created[parent].children if parent >= 0 else entry.children
                    )
                    siblings.append(child)

            result.append(entry)

        return result

    return entries(nav)


def render_toc(options: TocOptions, entries: Sequence[TocEntry]) -> str:
    """Renders the table of contents."""

    from mkdocs_exporter.core import resources

    source = options.template or (
        importlib.resources.files(resources)
        .joinpath("toc.html")
        .read_text(encoding="utf-8")
    )

    return (
        Environment(autoescape=True)
        .from_string(source)
        .render(title=options.title, entries=entries)
    )


class Book:
    """Writes an aggregated document."""

    def __init__(self, parts: Sequence[Part], pdfs: Sequence[bytes]) -> None:
        self.parts = list(parts)
        self.writer = PdfWriter()
        self.starts: dict[str, int] = {}

        for part, pdf in zip(self.parts, pdfs, strict=True):
            if part.blank_before and len(self.writer.pages):
                box = self.writer.pages[-1].mediabox
                self.writer.add_blank_page(
                    width=float(box.width), height=float(box.height)
                )

            self.starts[part.document.id] = len(self.writer.pages)
            self.writer.append(io.BytesIO(pdf), import_outline=False)

    def locate(self, part: Part, position: Position) -> tuple[int, Fit]:
        """The page index and destination fit of a position within a part."""

        index = min(
            self.starts[part.document.id] + position.page, len(self.writer.pages) - 1
        )
        height = float(self.writer.pages[index].mediabox.height)
        top = max(0.0, height - position.top * POINTS_PER_PIXEL)

        return index, Fit.xyz(left=0, top=top)

    def _destination(self, part: Part, position: Position) -> ArrayObject:
        """An explicit destination (page and position) within a part."""

        index, fit = self.locate(part, position)

        return ArrayObject(
            [
                self.writer.pages[index].indirect_reference,
                NameObject("/XYZ"),
                FloatObject(0),
                FloatObject(fit.fit_args[1]),
                NullObject(),
            ]
        )

    def anchor(self) -> None:
        """Resolves the links to named destinations within each part.

        Chromium names destinations after the identifiers of elements: once documents are
        merged, names repeated across documents (e.g. footnotes) would all point to the
        first document. They are replaced by explicit destinations in their own part.
        """

        bounds = sorted(
            (start, part)
            for part in self.parts
            for start in [self.starts[part.document.id]]
        )

        for index, page in enumerate(self.writer.pages):
            part = next((p for start, p in reversed(bounds) if start <= index), None)

            if part is None:
                continue

            for reference in page.get("/Annots") or []:
                annotation = reference.get_object()
                action = annotation.get("/A")
                action = action.get_object() if action is not None else None
                name = annotation.get("/Dest")

                if name is None and action is not None and action.get("/S") == "/GoTo":
                    name = action.get("/D")
                if not isinstance(name, str):
                    continue

                position = part.layout.anchors.get(str(name).lstrip("/"))

                if position is None:
                    continue

                destination = self._destination(part, position)

                if "/Dest" in annotation:
                    annotation[NameObject("/Dest")] = destination
                else:
                    action[NameObject("/D")] = destination

    def link(self, base: str, relative_to: str | None) -> None:
        """Turns links to aggregated documents into links within the document.

        Links to other pages of the website are made relative to the document's
        directory when `relative_to` is set.
        """

        parts = {part.document.url: part for part in self.parts}

        for _, annotation, uri in link_actions(self.writer):
            if not uri.startswith(base):
                continue

            target = uri[len(base) :]
            path, _, fragment = target.partition("#")
            part = parts.get(path.partition("?")[0])

            if part is not None:
                position = part.layout.anchors.get(fragment) if fragment else None
                destination = self._destination(part, position or part.start())
                annotation[NameObject("/A")] = DictionaryObject(
                    {
                        NameObject("/S"): NameObject("/GoTo"),
                        NameObject("/D"): destination,
                    }
                )
            elif relative_to is not None:
                action = cast(DictionaryObject, annotation["/A"].get_object())
                action[NameObject("/URI")] = TextStringObject(
                    relative_url(target, relative_to)
                )

    def outline(self, nav: Sequence[NavNode], depth: int) -> None:
        """Adds bookmarks: sections, documents and their headings."""

        if depth < 1:
            return

        parts = {part.document.id: part for part in self.parts}

        def add(nodes: Sequence[NavNode], parent: IndirectObject | None) -> None:
            for node in nodes:
                part = _first(node, parts)

                if part is None:
                    continue

                index, fit = self.locate(part, part.start())
                item = self.writer.add_outline_item(
                    title=node.title or part.document.title,
                    page_number=index,
                    parent=parent,
                    fit=fit,
                )

                if node.document is None:
                    add(node.children, item)
                    continue

                items: dict[int, IndirectObject] = {}

                for index, heading, parent_index in _nested(_sub_headings(part), depth):
                    page, heading_fit = self.locate(part, heading.position)
                    items[index] = self.writer.add_outline_item(
                        title=heading.title,
                        page_number=page,
                        parent=items[parent_index] if parent_index >= 0 else item,
                        fit=heading_fit,
                        is_open=False,
                    )

        add(nav, None)

    def write(self, output: Path, info: Mapping[str, object]) -> None:
        """Writes the document."""

        self.writer.add_metadata({"/Producer": "MkDocs Exporter", **metadata(info)})
        output.parent.mkdir(parents=True, exist_ok=True)

        with output.open("wb") as file:
            self.writer.write(file)


async def aggregate(
    renderer: Renderer,
    aggregation: Aggregation,
    layouts: Mapping[str, Layout],
    site: Site,
    name: str = "aggregate",
) -> list[Outcome]:
    """Renders the documents of an aggregation again and combines them.

    Page counts are predicted from the documents rendered with all their covers. When
    removing covers changes the layout (e.g. content reflowing onto a cover's page), or
    when the table of contents changes, the documents are numbered from their actual
    layout and rendered again.

    Returns:
        The documents that could not be rendered (the aggregation is then not written).
    """

    from mkdocs_exporter.core.renderer import Pass

    documents = [
        document for document in aggregation.documents if document.id in layouts
    ]
    output = aggregation.output.lstrip("/")
    directory = posixpath.dirname(output)
    nav = aggregation.nav if aggregation.nav is not None else flat_nav(documents)

    if not documents:
        return []

    logger.info("[mkdocs-exporter.pdf] Aggregating pages to '%s'...", output)

    parts = plan(documents, layouts, aggregation.covers, aggregation.start)
    toc = _toc(aggregation, nav, parts, site)
    results: dict[str, Outcome] = {}
    rendered: dict[str, Pass] = {}

    def passes() -> dict[str, Pass]:
        total = total_pages(parts)

        return {
            part.document.id: Pass(
                covers=part.covers,
                page=part.first_page,
                pages=total,
                name=name,
                directory=directory,
                relativize=False,
                toc=toc if index == 0 else None,
            )
            for index, part in enumerate(parts)
        }

    async def render(pending: Sequence[Document], parameters: dict[str, Pass]) -> bool:
        """Renders documents, returning whether they all succeeded."""

        outcomes = await renderer.render_all(
            pending, [parameters[document.id] for document in pending]
        )

        for outcome in outcomes:
            results[outcome.document.id] = outcome
            rendered[outcome.document.id] = parameters[outcome.document.id]

        return all(outcome.error is None for outcome in outcomes)

    if toc is not None and len(documents) > 1:
        # The length of the table of contents shifts every following page: measure it
        # first, so that the other documents are numbered right from the start.
        if not await render(documents[:1], passes()):
            return _failures(results)

        layout = _layout(results[documents[0].id])
        parts = renumber(
            parts, [layout, *(part.layout for part in parts[1:])], aggregation.start
        )
        toc = _toc(aggregation, nav, parts, site)

    attempts = 4 if aggregation.toc is not None else 3

    for attempt in range(attempts):
        # Only documents whose numbering (or table of contents) changed are rendered.
        parameters = passes()
        pending = [d for d in documents if rendered.get(d.id) != parameters[d.id]]

        if not await render(pending, parameters):
            return _failures(results)

        actual = renumber(
            parts, [_layout(results[d.id]) for d in documents], aggregation.start
        )
        updated = _toc(aggregation, nav, actual, site)
        stable = [p.pages for p in actual] == [
            p.pages for p in parts
        ] and updated == toc
        parts = actual
        toc = updated

        if stable:
            break
        if attempt == attempts - 1:
            logger.warning(
                "[mkdocs-exporter.pdf] The page numbering of '%s' did not stabilize, "
                "page numbers may be inaccurate",
                output,
            )
            break

        logger.debug("[mkdocs-exporter.pdf] Page numbering of '%s' changed", output)

    book = Book(parts, [_result(results[d.id]).pdf for d in documents])
    base = renderer.options.links or RELATIVE_LINKS_BASE

    book.anchor()
    book.link(base, directory if renderer.options.links is None else None)
    book.outline(nav, aggregation.outline)
    book.write(site.directory / output, aggregation.metadata)

    return []


def _result(outcome: Outcome) -> PrintResult:
    """The result of a successful rendering."""

    if outcome.result is None:  # pragma: no cover - failures are handled beforehand
        raise RuntimeError(f"'{outcome.document.id}' was not rendered")

    return outcome.result


def _layout(outcome: Outcome) -> Layout:
    """The layout of a successfully rendered document."""

    return _result(outcome).layout


def _failures(results: Mapping[str, Outcome]) -> list[Outcome]:
    """The documents that could not be rendered."""

    return [outcome for outcome in results.values() if outcome.error is not None]


def _toc(
    aggregation: Aggregation, nav: Sequence[NavNode], parts: Sequence[Part], site: Site
) -> str | None:
    """Renders the table of contents of an aggregation, if any."""

    if aggregation.toc is None:
        return None

    entries = toc_entries(nav, parts, aggregation.toc.depth, site.prefix)

    return render_toc(aggregation.toc, entries)
