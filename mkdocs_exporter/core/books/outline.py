from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    Fit,
    FloatObject,
    NullObject,
)

from mkdocs_exporter.core import toc
from mkdocs_exporter.core.books.assembly import Part
from mkdocs_exporter.core.document import Document
from mkdocs_exporter.core.toc import TocEntry


@dataclass
class NavNode:
    """An entry of the navigation: a section or a document."""

    title: str
    document: str | None = None
    """The identifier of the document (`None` for sections)."""

    children: list[NavNode] = field(default_factory=list)


def flat_nav(documents: Sequence[Document]) -> list[NavNode]:
    """A navigation listing documents."""

    return [
        NavNode(title=document.title, document=document.id) for document in documents
    ]


# --- Measurements ----------------------------------------------------------------------


def _first(node: NavNode, parts: Mapping[str, Part]) -> Part | None:
    """The first part of a navigation entry."""

    if node.document is not None:
        return parts.get(node.document)

    for child in node.children:
        if (part := _first(child, parts)) is not None:
            return part

    return None


def toc_entries(
    nav: Sequence[NavNode],
    parts: Mapping[str, Part],
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
    parts: Mapping[str, Part],
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
