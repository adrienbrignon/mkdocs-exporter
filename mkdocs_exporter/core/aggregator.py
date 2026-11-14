"""Combines documents into a single PDF document."""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfWriter

from mkdocs_exporter.core.document import Document, Layout

COVER_MODES = ("all", "none", "limits", "book", "front", "back")
"""How cover pages are handled when aggregating documents."""


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
class Part:
    """A document within the aggregated document."""

    document: Document
    covers: set[str]
    """The covers kept."""

    first_page: int
    """The number of its first page in the aggregated document."""

    pages: int
    """Its (expected) number of pages in the aggregated document."""


def plan(
    documents: Sequence[Document], layouts: Mapping[str, Layout], mode: str
) -> list[Part]:
    """Plans the aggregated document from the layout of each rendered document."""

    parts = []
    page = 1

    for index, document in enumerate(documents):
        layout = layouts[document.id]
        covers = kept_covers(mode, index, len(documents)) & set(document.covers)
        removed = set(document.covers) - covers
        pages = layout.pages - sum(
            layout.cover_pages.get(cover, 0) for cover in removed
        )

        parts.append(
            Part(document=document, covers=covers, first_page=page, pages=pages)
        )
        page += pages

    return parts


def renumber(parts: Sequence[Part], pages: Sequence[int]) -> list[Part]:
    """Plans the aggregated document again from the actual page count of each part."""

    result = []
    page = 1

    for part, count in zip(parts, pages, strict=True):
        result.append(
            Part(
                document=part.document, covers=part.covers, first_page=page, pages=count
            )
        )
        page += count

    return result


def metadata(values: Mapping[str, object]) -> dict[str, str]:
    """Normalizes document information keys (`title` → `/Title`)."""

    result = {}

    for key, value in values.items():
        if value is None:
            continue

        name = key if key.startswith("/") else "/" + key[:1].upper() + key[1:]
        result[name] = str(value)

    return result


def combine(pdfs: Sequence[bytes], output: Path, info: Mapping[str, object]) -> None:
    """Writes the concatenation of PDF documents."""

    writer = PdfWriter()

    for pdf in pdfs:
        writer.append(io.BytesIO(pdf))

    writer.add_metadata({"/Producer": "MkDocs Exporter", **metadata(info)})
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("wb") as file:
        writer.write(file)
