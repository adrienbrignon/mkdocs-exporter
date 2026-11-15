from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from mkdocs_exporter.core import css

PLACEHOLDERS = ("site_name", "page_title", "section", "page", "pages")
"""The placeholders available in headers and footers."""

POSITIONS = {
    "header": {"left": "top-left", "center": "top-center", "right": "top-right"},
    "footer": {
        "left": "bottom-left",
        "center": "bottom-center",
        "right": "bottom-right",
    },
}
"""The page margin box of each position of headers and footers."""

ALL_BOXES = (
    "top-left-corner",
    "top-left",
    "top-center",
    "top-right",
    "top-right-corner",
    "right-top",
    "right-middle",
    "right-bottom",
    "bottom-right-corner",
    "bottom-right",
    "bottom-center",
    "bottom-left",
    "bottom-left-corner",
    "left-bottom",
    "left-middle",
    "left-top",
)
"""Every page margin box."""

STYLE = "font-family: sans-serif; font-size: 9pt; color: #555; white-space: pre;"
"""The style of the margin boxes of headers and footers."""

SECTIONS = "mkdocs-exporter-section"
"""The counter style printing the section of each page (see `sections`)."""

COVER_PAGE = "mkdocs-exporter-cover"
"""The named page of back covers, without headers nor footers."""

PLACEHOLDER = re.compile(r"\{([^{}]*)\}")


def validate(template: str) -> None:
    """Raises a `ValueError` when a template uses an unknown placeholder."""

    for match in PLACEHOLDER.finditer(template):
        if match.group(1) not in PLACEHOLDERS:
            raise ValueError(
                f"unknown placeholder {match.group(0)!r} "
                f"(available: {', '.join('{' + name + '}' for name in PLACEHOLDERS)})"
            )


def content(template: str, values: Mapping[str, str]) -> str:
    """The `content` of a margin box showing a template.

    Args:
        template: The text, with placeholders.
        values: The values of the placeholders known in advance (`site_name`,
            `page_title`); page numbers and sections are counters.
    """

    validate(template)

    counters = {
        "page": "counter(page)",
        "pages": "counter(pages)",
        "section": f"counter(page, {SECTIONS})",
    }
    parts = []
    position = 0

    for match in PLACEHOLDER.finditer(template):
        if match.start() > position:
            parts.append(css.string(template[position : match.start()]))

        name = match.group(1)
        parts.append(counters.get(name) or css.string(values.get(name, "")))
        position = match.end()

    if position < len(template):
        parts.append(css.string(template[position:]))

    return " ".join(parts) or '""'


@dataclass(frozen=True)
class Margins:
    """Headers and footers: the template shown by each page margin box."""

    boxes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def of(cls, templates: Mapping[str, Mapping[str, str | None]]) -> Margins:
        """Headers and footers, from templates by location (`header`, `footer`) and
        position (`left`, `center`, `right`)."""

        return cls(
            {
                POSITIONS[location][position]: template
                for location, positions in templates.items()
                for position, template in positions.items()
                if template is not None
            }
        )

    def uses(self, placeholder: str) -> bool:
        """Does a header or a footer show a placeholder?"""

        return any("{" + placeholder + "}" in text for text in self.boxes.values())

    def stylesheet(self, values: Mapping[str, str], front_cover: bool = False) -> str:
        """The stylesheet printing headers and footers in a page's document.

        They are left out of covers: the front cover is the first page, the back cover
        is moved to a named page of its own.
        """

        if not self.boxes:
            return ""

        return "".join(
            [
                _section_styles(),
                _page("", self.boxes, values),
                f".mkdocs-exporter-back-cover {{ page: {COVER_PAGE}; }}\n",
                _empty(COVER_PAGE, self.boxes),
                _empty(":first", self.boxes) if front_cover else "",
            ]
        )

    def book_stylesheet(
        self,
        values: Mapping[str, str],
        titles: Mapping[str, str],
        hidden: Iterable[str],
        blank: str,
    ) -> str:
        """The stylesheet printing the headers and footers of a book.

        Args:
            values: The values of the placeholders (`site_name`).
            titles: The `{page_title}` of named pages (e.g. the content of each part).
            hidden: Named pages without headers nor footers (covers).
            blank: The named page of blank pages, where every margin box is emptied
                (even those of other stylesheets).
        """

        titled = {
            box: text for box, text in self.boxes.items() if "{page_title}" in text
        }

        return "".join(
            [
                _section_styles(),
                _page("", self.boxes, {**values, "page_title": ""}),
                *(
                    _page(name, titled, {**values, "page_title": title})
                    for name, title in titles.items()
                ),
                *(_empty(name, self.boxes) for name in hidden),
                _empty(blank, ALL_BOXES, important=True),
            ]
        )


def sections(titles: Sequence[str]) -> str:
    """The counter style printing the section of each page (by page number)."""

    symbols = " ".join(css.string(title) for title in titles) or '""'

    return (
        f"@counter-style {SECTIONS} {{ system: fixed 1; "
        f"symbols: {symbols}; fallback: {SECTIONS}-none; }}\n"
    )


def running_heads(
    headings: Iterable[tuple[int, str]], pages: Iterable[int]
) -> dict[int, str]:
    """The section of pages: their first heading, or the last heading of the previous
    pages.

    Args:
        headings: The page and title of the headings to follow, in order.
        pages: The pages, in order.
    """

    first: dict[int, str] = {}
    last: dict[int, str] = {}

    for page, title in headings:
        first.setdefault(page, title)
        last[page] = title

    heads = {}
    current = ""

    for page in pages:
        heads[page] = first.get(page, current)
        current = last.get(page, current)

    return heads


def _section_styles() -> str:
    """The counter styles of sections, until they are known (see `sections`)."""

    return (
        f'@counter-style {SECTIONS}-none {{ system: cyclic; symbols: ""; }}\n'
        + sections([])
    )


def _page(selector: str, boxes: Mapping[str, str], values: Mapping[str, str]) -> str:
    """A `@page` rule showing templates in margin boxes."""

    if not boxes:
        return ""

    rules = "\n".join(
        f"  @{box} {{ content: {content(text, values)}; {STYLE} }}"
        for box, text in boxes.items()
    )

    return f"@page {selector} {{\n{rules}\n}}\n"


def _empty(selector: str, boxes: Iterable[str], important: bool = False) -> str:
    """A `@page` rule emptying margin boxes."""

    value = "none !important" if important else "none"
    rules = "\n".join(f"  @{box} {{ content: {value}; }}" for box in boxes)

    return f"@page {selector} {{\n{rules}\n}}\n" if rules else ""
