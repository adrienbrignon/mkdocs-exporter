from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import Destination


@dataclass(frozen=True)
class Link:
    """A link annotation."""

    page: int
    """The (0-based) index of the page holding the link."""

    uri: str | None = None
    """The target URI of an external link."""

    target_page: int | None = None
    """The (0-based) index of the page targeted by an internal link."""


@dataclass(frozen=True)
class OutlineItem:
    """A PDF outline (bookmark) item."""

    title: str
    page: int | None
    children: list[OutlineItem] = field(default_factory=list)
    top: float | None = None
    """The position it shows (from the bottom of the page, in points), if any."""


class PdfDocument:
    """A read-only view over a PDF document, tailored for assertions."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.reader = PdfReader(path)

    @property
    def page_count(self) -> int:
        """The number of pages."""

        return len(self.reader.pages)

    @cached_property
    def pages_text(self) -> list[str]:
        """The text of each page."""

        return [page.extract_text() or "" for page in self.reader.pages]

    @property
    def tagged(self) -> bool:
        """Is the document tagged (does it describe its structure)?"""

        root = self.reader.trailer["/Root"]

        return "/StructTreeRoot" in root and bool(
            (root.get("/MarkInfo") or {}).get("/Marked")
        )

    @property
    def text(self) -> str:
        """The text of the whole document."""

        return "\n".join(self.pages_text)

    def pages_containing(self, needle: str) -> list[int]:
        """The (0-based) indexes of the pages containing some text."""

        return [i for i, text in enumerate(self.pages_text) if needle in text]

    def count(self, needle: str) -> int:
        """The number of occurrences of some text in the document."""

        return self.text.count(needle)

    @cached_property
    def links(self) -> list[Link]:
        """The link annotations of the document."""

        links = []

        for index, page in enumerate(self.reader.pages):
            for reference in page.get("/Annots") or []:
                annotation = reference.get_object()

                if annotation.get("/Subtype") != "/Link":
                    continue

                action = annotation.get("/A")
                action = action.get_object() if action is not None else {}

                if "/URI" in action:
                    links.append(Link(page=index, uri=str(action["/URI"])))
                else:
                    target = action.get("/D", annotation.get("/Dest"))
                    links.append(Link(page=index, target_page=self._resolve(target)))

        return links

    @property
    def external_links(self) -> set[str]:
        """The URIs of external links."""

        return {link.uri for link in self.links if link.uri is not None}

    @property
    def internal_links(self) -> list[Link]:
        """Links pointing to a page of this document."""

        return [link for link in self.links if link.uri is None]

    @cached_property
    def outline(self) -> list[OutlineItem]:
        """The outline (bookmarks) of the document."""

        def convert(items: list) -> list[OutlineItem]:
            result: list[OutlineItem] = []

            for item in items:
                if isinstance(item, list):
                    if result:
                        result[-1].children.extend(convert(item))
                    continue

                page = self.reader.get_destination_page_number(item)
                top = item.get("/Top")
                result.append(
                    OutlineItem(
                        title=str(item.title),
                        page=page,
                        top=None if top is None else float(top),
                    )
                )

            return result

        return convert(self.reader.outline)

    @property
    def metadata(self) -> dict[str, str]:
        """The document information dictionary."""

        return {key: str(value) for key, value in (self.reader.metadata or {}).items()}

    def baseline(self, needle: str, page: int) -> tuple[float, float] | None:
        """The baseline (from the bottom, in points) and size of a text on a page."""

        found: list[tuple[float, float]] = []

        def visit(text: str, cm: list, tm: list, font: object, size: float) -> None:
            if not found and text.strip().startswith(needle):
                scale = math.hypot(tm[0], tm[1]) * math.hypot(cm[0], cm[1])
                found.append((tm[5] * cm[3] + cm[5], size * scale))

        self.reader.pages[page].extract_text(visitor_text=visit)

        return found[0] if found else None

    def font_size(self, needle: str) -> float | None:
        """The size (in points, as printed) of the first text starting with `needle`."""

        sizes: list[float] = []

        def visit(text: str, cm: list, tm: list, font: object, size: float) -> None:
            if not sizes and text.strip().startswith(needle):
                scale = math.hypot(tm[0], tm[1]) * math.hypot(cm[0], cm[1])
                sizes.append(round(size * scale, 1))

        for page in self.reader.pages:
            page.extract_text(visitor_text=visit)

            if sizes:
                return sizes[0]

        return None

    def image_count(self) -> int:
        """The number of images drawn in the document."""

        return sum(len(page.images) for page in self.reader.pages)

    def _resolve(self, target: object) -> int | None:
        """Resolves an internal link target to a page index."""

        if target is None:
            return None
        if isinstance(target, Destination):
            return self.reader.get_destination_page_number(target)

        target = getattr(target, "get_object", lambda: target)()

        if isinstance(target, str):
            destination = self.reader.named_destinations.get(target)

            return (
                None
                if destination is None
                else self.reader.get_destination_page_number(destination)
            )
        if isinstance(target, list) and target:
            return self.reader.get_page_number(target[0].get_object())

        return None
