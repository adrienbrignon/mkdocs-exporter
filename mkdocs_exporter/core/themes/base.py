from __future__ import annotations

import importlib.resources
from typing import ClassVar

from mkdocs_exporter.core.html import HtmlDocument


class Theme:
    """A theme: knows how to adapt the pages it produces for printing."""

    name: ClassVar[str] = "generic"
    """The name of the theme."""

    hidden: ClassVar[tuple[str, ...]] = ()
    """Selectors of elements that must not appear in PDF documents."""

    removed: ClassVar[tuple[str, ...]] = ()
    """Selectors of elements removed before the theme's scripts run.

    Only for elements whose removal the theme's scripts tolerate (others are hidden).
    """

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
