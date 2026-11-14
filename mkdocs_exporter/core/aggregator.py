"""Combines documents into a single PDF document."""

from __future__ import annotations

import io
import posixpath
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pypdf import PdfWriter

from mkdocs_exporter.core.document import Document, Layout, Site
from mkdocs_exporter.logging import logger

if TYPE_CHECKING:
    from pathlib import Path

    from mkdocs_exporter.core.renderer import Outcome, Renderer

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
class Aggregation:
    """A document combining several documents."""

    output: str
    """The location of the combined document, relative to the website's root."""

    documents: Sequence[Document]
    """The documents to combine, in order."""

    covers: str = "all"
    """How cover pages are handled (see `kept_covers`)."""

    metadata: Mapping[str, object] = field(default_factory=dict)
    """The document information (title, author...)."""


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


async def aggregate(
    renderer: Renderer,
    aggregation: Aggregation,
    layouts: Mapping[str, Layout],
    site: Site,
    name: str = "aggregate",
) -> list[Outcome]:
    """Renders the documents of an aggregation again and combines them.

    Page counts are predicted from the documents rendered with all their covers. When
    removing covers changes the layout (e.g. content reflowing onto a cover's page), the
    documents are numbered from their actual page counts and rendered again.

    Returns:
        The documents that could not be rendered (the aggregation is then not written).
    """

    from mkdocs_exporter.core.renderer import Pass

    documents = [
        document for document in aggregation.documents if document.id in layouts
    ]
    output = aggregation.output.lstrip("/")

    if not documents:
        return []

    logger.info("[mkdocs-exporter.pdf] Aggregating pages to '%s'...", output)

    parts = plan(documents, layouts, aggregation.covers)

    for attempt in range(3):
        total = sum(part.pages for part in parts)
        passes = [
            Pass(
                covers=part.covers,
                page=part.first_page,
                pages=total,
                name=name,
                directory=posixpath.dirname(output),
            )
            for part in parts
        ]
        results = await renderer.render_all(documents, passes)
        failures = [outcome for outcome in results if outcome.error is not None]

        if failures:
            return failures

        pages = [o.result.layout.pages for o in results if o.result is not None]

        if pages == [part.pages for part in parts]:
            break
        if attempt == 2:
            logger.warning(
                "[mkdocs-exporter.pdf] The page numbering of '%s' did not stabilize, "
                "page numbers may be inaccurate",
                output,
            )
            break

        logger.debug("[mkdocs-exporter.pdf] Page numbering of '%s' changed", output)
        parts = renumber(parts, pages)

    combine(
        [outcome.result.pdf for outcome in results if outcome.result is not None],
        site.directory / output,
        aggregation.metadata,
    )

    return []
