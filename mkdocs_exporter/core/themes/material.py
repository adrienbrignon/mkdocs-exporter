"""The Material for MkDocs theme."""

from __future__ import annotations

from functools import cache
from types import SimpleNamespace
from typing import Any

from bs4 import BeautifulSoup

from mkdocs_exporter.core.html import HtmlDocument
from mkdocs_exporter.core.themes.base import Theme


class MaterialTheme(Theme):
    """The `material` theme."""

    name = "material"
    hidden = (
        ".md-sidebar.md-sidebar--primary",
        ".md-sidebar.md-sidebar--secondary",
        "header.md-header",
        ".md-container > nav",
        "nav.md-tags",
    )
    # Without its search box, Material doesn't load the search index in every document
    # (the index grows with the website: loading it in every page is quadratic).
    removed = ('[data-md-component="search"]',)
    content = "article.md-content__inner"
    stylesheet = "material.css"
    script = "material.js"

    def button(
        self, document: HtmlDocument, title: str, icon: str, attributes: dict[str, str]
    ) -> None:
        """Inserts a button next to Material's own content buttons."""

        attrs = {"title": title, "class": "md-content__button md-icon", **attributes}
        button = document.soup.new_tag("a", attrs=attrs)
        svg = self.icon(icon) or self.icon("material-progress-question")

        if svg is not None:
            button.append(BeautifulSoup(svg, "html.parser"))

        tags = document.select_one("nav.md-tags")

        if tags is not None:
            tags.insert_after(button)
        else:
            self.content_element(document).insert(0, button)

    def icon(self, name: str) -> str | None:
        """Returns the SVG markup of a Material icon (e.g. `material-file-download`)."""

        markdown = _markdown()

        if markdown is None:
            return None

        from material.extensions.emoji import to_svg

        shortname = ":" + name.strip(":") + ":"

        try:
            element = to_svg(
                "twemoji", shortname, None, None, None, None, None, {}, markdown
            )
        except KeyError:
            return None

        return None if element is None else str(element.text)


@cache
def _markdown() -> Any:
    """A stand-in for the Python-Markdown instance Material's emoji generator expects."""

    try:
        from material.extensions.emoji import twemoji
    except ImportError:
        return None

    class Stash:
        def store(self, value: Any) -> Any:
            return value

    return SimpleNamespace(
        htmlStash=Stash(),
        inlinePatterns={"emoji": SimpleNamespace(emoji_index=twemoji({}, None))},
    )
