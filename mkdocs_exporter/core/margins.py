"""Headers and footers, generated as CSS page margin boxes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from mkdocs_exporter.core.document import Layout

PLACEHOLDERS = ("site_name", "page_title", "section", "page", "pages")
"""The placeholders available in headers and footers."""

BOXES = {
    "header": {"left": "top-left", "center": "top-center", "right": "top-right"},
    "footer": {
        "left": "bottom-left",
        "center": "bottom-center",
        "right": "bottom-right",
    },
}
"""The page margin boxes of each position of headers and footers."""

SECTIONS = "mkdocs-exporter-section"
"""The counter style printing the current section of each page (see `sections`)."""

TOKEN = re.compile(r"\{([^{}]*)\}")


def validate(template: str) -> None:
    """Raises a `ValueError` when a template uses an unknown placeholder."""

    for match in TOKEN.finditer(template):
        if match.group(1) not in PLACEHOLDERS:
            raise ValueError(
                f"unknown placeholder {match.group(0)!r} "
                f"(available: {', '.join('{' + name + '}' for name in PLACEHOLDERS)})"
            )


def uses(templates: Mapping[str, Mapping[str, str | None]], placeholder: str) -> bool:
    """Does a header or a footer use a placeholder?"""

    return any(
        "{" + placeholder + "}" in (template or "")
        for positions in templates.values()
        for template in positions.values()
    )


def css_string(text: str) -> str:
    """Quotes a text as a CSS string."""

    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\A ")

    return f'"{escaped}"'


def content(template: str, values: Mapping[str, str], pages: int | None = None) -> str:
    """The value of the `content` property of a margin box.

    Args:
        template: The text, with placeholders.
        values: The values of placeholders (`site_name`, `page_title`).
        pages: The total number of pages, when it differs from the document's own.
    """

    validate(template)

    parts = []
    position = 0

    for match in TOKEN.finditer(template):
        if match.start() > position:
            parts.append(css_string(template[position : match.start()]))

        name = match.group(1)

        if name == "page":
            parts.append("counter(page)")
        elif name == "pages":
            parts.append("counter(pages)" if pages is None else css_string(str(pages)))
        elif name == "section":
            parts.append(f"counter(page, {SECTIONS})")
        else:
            parts.append(css_string(values.get(name, "")))

        position = match.end()

    if position < len(template):
        parts.append(css_string(template[position:]))

    return " ".join(parts) or '""'


def stylesheet(
    templates: Mapping[str, Mapping[str, str | None]],
    values: Mapping[str, str],
    front_cover: bool = False,
    first_page: int | None = None,
    pages: int | None = None,
) -> str:
    """The stylesheet rendering headers and footers.

    Headers and footers are hidden on cover pages: the front cover is expected on the
    first page, the back cover is moved to a page of its own (a named page).

    Args:
        templates: Templates by location (`header`, `footer`) and position (`left`,
            `center`, `right`).
        values: The values of placeholders (`site_name`, `page_title`).
        front_cover: Does the document start with a front cover?
        first_page: The number of the first page (when part of a larger document).
        pages: The total number of pages (when part of a larger document).
    """

    boxes = {
        BOXES[location][position]: template
        for location, positions in templates.items()
        for position, template in positions.items()
        if template is not None
    }
    first = [f"  counter-set: page {first_page};"] if first_page is not None else []

    if not boxes:
        return f"@page :first {{\n{first[0]}\n}}\n" if first else ""

    style = "font-family: sans-serif; font-size: 9pt; color: #555; white-space: pre;"
    rules = "\n".join(
        f"  @{box} {{ content: {content(template, values, pages)}; {style} }}"
        for box, template in boxes.items()
    )
    empty = [f"  @{box} {{ content: none; }}" for box in boxes]
    first += empty if front_cover else []

    return (
        f'@counter-style {SECTIONS}-none {{ system: cyclic; symbols: ""; }}\n'
        + sections([])
        + f"@page {{\n{rules}\n}}\n"
        ".mkdocs-exporter-back-cover { page: mkdocs-exporter-cover; }\n"
        "@page mkdocs-exporter-cover {\n"
        + "\n".join(empty)
        + "\n}\n"
        + ("@page :first {\n" + "\n".join(first) + "\n}\n" if first else "")
    )


def sections(titles: Sequence[str], first_page: int = 1) -> str:
    """The counter style printing the section of each page (by page number)."""

    symbols = " ".join(css_string(title) for title in titles) or '""'

    return (
        f"@counter-style {SECTIONS} {{ system: fixed {first_page}; "
        f"symbols: {symbols}; fallback: {SECTIONS}-none; }}\n"
    )


def running_heads(headings: Sequence[tuple[str, str]], layout: Layout) -> list[str]:
    """The section of each page: its first heading, or the last one of previous pages.

    Args:
        headings: The identifier and title of the headings to follow, in order.
        layout: The layout of the document (positions of the headings).
    """

    first: dict[int, str] = {}
    last: dict[int, str] = {}

    for identifier, title in headings:
        position = layout.anchors.get(identifier)

        if position is None:
            continue

        first.setdefault(position.page, title)
        last[position.page] = title

    result = []
    current = ""

    for page in range(layout.pages):
        result.append(first.get(page, current))
        current = last.get(page, current)

    return result
