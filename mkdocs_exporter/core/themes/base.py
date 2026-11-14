"""The base theme."""

from __future__ import annotations

import importlib.resources
import re
from typing import ClassVar

from mkdocs_exporter.core.html import HtmlDocument

NTH_SELECTOR = re.compile(
    r":nth-(child|last-child|of-type|last-of-type)\(\s*(\d*)\s*n\s*\+\s*(\d+)\s*\)"
)


def fix_nth_selectors(css: str) -> str:
    """Rewrites `:nth-*(An+B)` selectors as `:nth-*(An-C)` when equivalent.

    Paged.js mistakes the `+` of such selectors for a sibling combinator and fails to
    paginate the document. `An+B` and `An-(A-B)` match the same elements when `0 < B < A`.
    """

    def replace(match: re.Match[str]) -> str:
        kind, a, b = match.group(1), int(match.group(2) or 1), int(match.group(3))

        if 0 < b < a:
            return f":nth-{kind}({a}n-{a - b})"

        return match.group(0)

    return NTH_SELECTOR.sub(replace, css)


class Theme:
    """A theme: knows how to adapt the pages it produces for printing."""

    name: ClassVar[str] = "generic"
    """The name of the theme."""

    hidden: ClassVar[tuple[str, ...]] = ()
    """Selectors of elements that must not appear in PDF documents."""

    content: ClassVar[str] = "main, [role='main'], article"
    """Selector of the element holding the page's content."""

    stylesheet: ClassVar[str | None] = None
    """The name of the bundled stylesheet applied to PDF documents."""

    script: ClassVar[str | None] = None
    """The name of the bundled script loaded (before the website's) in PDF documents."""

    def print_stylesheet(self) -> str:
        """The stylesheet applied to PDF documents for this theme."""

        if self.stylesheet is None:
            return ""

        from mkdocs_exporter.core.resources import css

        return (
            importlib.resources.files(css)
            .joinpath(self.stylesheet)
            .read_text(encoding="utf-8")
        )

    def print_script(self) -> str:
        """The script loaded in PDF documents for this theme."""

        if self.script is None:
            return ""

        from mkdocs_exporter.core.resources import js

        return (
            importlib.resources.files(js)
            .joinpath(self.script)
            .read_text(encoding="utf-8")
        )

    def transform_stylesheet(self, css: str) -> str:
        """Transforms a stylesheet before it reaches Paged.js."""

        return fix_nth_selectors(css)

    def content_element(self, document: HtmlDocument):
        """The element holding the page's content (falls back to the body)."""

        return document.select_one(self.content) or document.body

    def button(
        self, document: HtmlDocument, title: str, icon: str, attributes: dict[str, str]
    ) -> None:
        """Inserts a button at the top of the page's content."""

        button = document.soup.new_tag("a", attrs={"title": title, **attributes})
        button.string = title

        self.content_element(document).insert(0, button)

    def icon(self, name: str) -> str | None:
        """Returns the SVG markup of an icon, when the theme provides icons."""

        return None
