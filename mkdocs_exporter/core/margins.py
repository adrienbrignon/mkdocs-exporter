"""Headers and footers, generated as CSS page margin boxes."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

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


def content(template: str, values: Mapping[str, str]) -> str:
    """The value of the `content` property of a margin box.

    Args:
        template: The text, with placeholders.
        values: The values of placeholders (`site_name`, `page_title`).
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
            parts.append("counter(pages)")
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
) -> str:
    """The stylesheet rendering headers and footers.

    Headers and footers are hidden on cover pages: the front cover is expected on the
    first page, the back cover is moved to a page of its own (a named page).

    Args:
        templates: Templates by location (`header`, `footer`) and position (`left`,
            `center`, `right`).
        values: The values of placeholders (`site_name`, `page_title`).
        front_cover: Does the document start with a front cover?
    """

    boxes = {
        BOXES[location][position]: template
        for location, positions in templates.items()
        for position, template in positions.items()
        if template is not None
    }

    if not boxes:
        return ""

    rules = "\n".join(
        f"  @{box} {{ content: {content(template, values)}; {STYLE} }}"
        for box, template in boxes.items()
    )
    empty = "\n".join(f"  @{box} {{ content: none; }}" for box in boxes)

    return (
        f'@counter-style {SECTIONS}-none {{ system: cyclic; symbols: ""; }}\n'
        + sections([])
        + f"@page {{\n{rules}\n}}\n"
        ".mkdocs-exporter-back-cover { page: mkdocs-exporter-cover; }\n"
        f"@page mkdocs-exporter-cover {{\n{empty}\n}}\n"
        + (f"@page :first {{\n{empty}\n}}\n" if front_cover else "")
    )


def book_stylesheet(
    templates: Mapping[str, Mapping[str, str | None]],
    values: Mapping[str, str],
    titles: Mapping[str, str],
    hidden: Iterable[str],
    blank: str,
) -> str:
    """The stylesheet rendering the headers and footers of a book (combined documents).

    Args:
        templates: Templates by location and position (see `stylesheet`).
        values: The values of placeholders (`site_name`).
        titles: The `{page_title}` of named pages (e.g. the content of each part).
        hidden: Named pages without headers nor footers (covers).
        blank: The named page of blank pages, where every margin box is emptied (even
            those of other stylesheets).
    """

    boxes = {
        BOXES[location][position]: template
        for location, positions in templates.items()
        for position, template in positions.items()
        if template is not None
    }
    titled = {
        box: template for box, template in boxes.items() if "{page_title}" in template
    }

    def page(selector: str, title: str, only: Mapping[str, str]) -> str:
        rules = "\n".join(
            f"  @{box} {{ content: "
            f"{content(template, {**values, 'page_title': title})}; {STYLE} }}"
            for box, template in only.items()
        )

        return f"@page {selector} {{\n{rules}\n}}\n" if rules else ""

    empty = "\n".join(f"  @{box} {{ content: none; }}" for box in boxes)
    css = [
        f'@counter-style {SECTIONS}-none {{ system: cyclic; symbols: ""; }}\n',
        sections([]),
        page("", "", boxes),
        *(page(name, title, titled) for name, title in titles.items()),
        *(f"@page {name} {{\n{empty}\n}}\n" for name in hidden if empty),
        f"@page {blank} {{\n"
        + "\n".join(f"  @{box} {{ content: none !important; }}" for box in ALL_BOXES)
        + "\n}\n",
    ]

    return "".join(css)


def sections(titles: Sequence[str]) -> str:
    """The counter style printing the section of each page (by page number)."""

    symbols = " ".join(css_string(title) for title in titles) or '""'

    return (
        f"@counter-style {SECTIONS} {{ system: fixed 1; "
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


UNITS = {
    "px": 1.0,
    "cm": 96 / 2.54,
    "mm": 96 / 25.4,
    "q": 96 / 101.6,
    "in": 96.0,
    "pt": 96 / 72,
    "pc": 16.0,
}
"""CSS pixels per unit (absolute units)."""


def to_pixels(length: str) -> float | None:
    """Converts a CSS length to pixels (`None` for relative lengths and keywords)."""

    match = re.fullmatch(r"\s*(-?[\d.]+)\s*([a-zA-Z]*)\s*", length)

    if match is None:
        return None

    unit = match.group(2).lower() or "px"

    return float(match.group(1)) * UNITS[unit] if unit in UNITS else None


def top_margin(
    rules: Sequence[Mapping[str, str]], name: str | None, first: bool, right: bool
) -> float:
    """The top margin (in pixels) of a page, from the `@page` rules setting one.

    Rules apply by specificity (page name, then `:first`, then `:left` / `:right`), then
    in order, as defined by CSS Paged Media.

    Args:
        rules: The `@page` rules (`selector`, `marginTop`), in order.
        name: The name of the page.
        first: Is it the document's first page?
        right: Is it a right page?
    """

    best: tuple[tuple[int, int, int], int] | None = None
    margin = 0.0

    for order, rule in enumerate(rules):
        value = to_pixels(str(rule.get("marginTop", "")))

        if value is None:
            continue

        for selector in str(rule.get("selector", "")).split(","):
            match = re.fullmatch(r"\s*([A-Za-z_][\w-]*)?((?::[\w-]+)*)\s*", selector)

            if match is None:
                continue

            page, pseudos = match.group(1), re.findall(r":([\w-]+)", match.group(2))

            if (
                (page and page != name)
                or ("first" in pseudos and not first)
                or "blank" in pseudos
                or ("left" in pseudos and right)
                or ("right" in pseudos and not right)
            ):
                continue

            specificity = (
                int(bool(page)),
                pseudos.count("first"),
                pseudos.count("left") + pseudos.count("right"),
            )

            if best is None or (specificity, order) >= best:
                best = (specificity, order)
                margin = value

    return margin
