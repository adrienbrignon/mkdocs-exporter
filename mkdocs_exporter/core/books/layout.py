from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from mkdocs_exporter.core import margins
from mkdocs_exporter.core.books.styles import (
    BACK_COVER_PAGE,
    BLANK_PAGE,
    TOC_PAGE,
    PageNames,
)
from mkdocs_exporter.core.css import PageMargin
from mkdocs_exporter.core.document import Heading, Position

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


def page_names(measure: Measure, names: PageNames) -> list[str | None]:
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
            mark(range(part.back[0], part.back[1] + 1), BACK_COVER_PAGE)

    if measure.toc:
        mark(range(measure.toc[0], measure.toc[1] + 1), TOC_PAGE)

    mark(iter(measure.blanks), BLANK_PAGE)

    return result
