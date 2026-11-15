"""Headers and footers, generated as CSS page margin boxes."""

from __future__ import annotations

import re
from collections.abc import Mapping

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

SECTION = "--mkdocs-exporter-section"
"""The CSS custom property holding the current section (set on each page by `pdf.js`)."""

TOKEN = re.compile(r"\{([^{}]*)\}")


def validate(template: str) -> None:
    """Raises a `ValueError` when a template uses an unknown placeholder."""

    for match in TOKEN.finditer(template):
        if match.group(1) not in PLACEHOLDERS:
            raise ValueError(
                f"unknown placeholder {match.group(0)!r} "
                f"(available: {', '.join('{' + name + '}' for name in PLACEHOLDERS)})"
            )


def css_string(text: str) -> str:
    """Quotes a text as a CSS string."""

    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\A ")

    return f'"{escaped}"'


def content(template: str, values: Mapping[str, str]) -> str:
    """The value of the `content` property of a margin box."""

    validate(template)

    parts = []
    position = 0

    for match in TOKEN.finditer(template):
        if match.start() > position:
            parts.append(css_string(template[position : match.start()]))

        name = match.group(1)

        if name in ("page", "pages"):
            parts.append(f"counter({name})")
        elif name == "section":
            parts.append(f'var({SECTION}, "")')
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

    Headers and footers are hidden on cover pages: the back cover is moved to a page of
    its own (a named page), the front cover is expected on the first page (Paged.js would
    insert an empty page before a named page starting the document).

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
        f"  @{box} {{ content: {content(template, values)}; white-space: pre; }}"
        for box, template in boxes.items()
    )
    empty = "\n".join(f"  @{box} {{ content: none; }}" for box in boxes)

    return (
        f"@page {{\n{rules}\n}}\n"
        ".mkdocs-exporter-back-cover { page: mkdocs-exporter-cover; }\n"
        f"@page mkdocs-exporter-cover {{\n{empty}\n}}\n"
        + (f"@page :first {{\n{empty}\n}}\n" if front_cover else "")
    )
