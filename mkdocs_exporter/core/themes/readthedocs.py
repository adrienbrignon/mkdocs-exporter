"""The Read the Docs theme."""

from __future__ import annotations

from mkdocs_exporter.core.html import HtmlDocument
from mkdocs_exporter.core.themes.base import Theme


class ReadTheDocsTheme(Theme):
    """The `readthedocs` theme."""

    name = "readthedocs"
    hidden = (".rst-content > div[role='navigation']", "nav.wy-nav-side")
    content = ".document, [role='main']"
    stylesheet = "readthedocs.css"

    def button(
        self, document: HtmlDocument, title: str, icon: str, attributes: dict[str, str]
    ) -> None:
        """Inserts a button at the top of the document."""

        attrs = {"title": title, "class": "btn btn-neutral float-right", **attributes}
        button = document.soup.new_tag("a", attrs=attrs)
        button.string = title

        self.content_element(document).insert(0, button)
