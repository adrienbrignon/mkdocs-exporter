from __future__ import annotations

import importlib.resources
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bs4 import Tag

from mkdocs_exporter.core import toc
from mkdocs_exporter.core.document import Document, Heading, Site
from mkdocs_exporter.core.html import (
    ANCESTOR,
    HtmlDocument,
    PageResources,
    page_resources,
    resolve_link,
    teleported,
)
from mkdocs_exporter.core.html import headings as find_headings
from mkdocs_exporter.core.pdf import RELATIVE_LINKS_BASE
from mkdocs_exporter.core.server import RESERVED
from mkdocs_exporter.core.themes import Theme
from mkdocs_exporter.core.toc import TocOptions

if TYPE_CHECKING:
    from mkdocs_exporter.core.renderer import RenderOptions

COVER_LOCATIONS = ("front", "back")
"""The locations of cover pages."""


@dataclass
class Prepared:
    """A page's content prepared for its own document, reused as a part of books.

    It spares books another parse of the page: the content is detached from the page's
    document once that document is printed, links resolved (see `rewrite_urls`'s
    `base`) and every cover inserted.
    """

    content: Tag
    resources: PageResources
    teleported: list[tuple[str, str, Tag]] = field(default_factory=list)
    """The elements the content teleports: (origin, destination, element), the origin
    being the location of the cover holding the element (`front`, `back`) or `content`."""


class Preparer:
    """Prepares the HTML printed for documents."""

    def __init__(self, site: Site, theme: Theme, options: RenderOptions) -> None:
        from mkdocs_exporter.core.resources import css

        self.site = site
        self.theme = theme
        self.options = options
        self.base_stylesheets = [
            importlib.resources.files(css).joinpath("base.css").read_text("utf-8"),
            theme.print_stylesheet(),
        ]

    def prepare_content(
        self, html: HtmlDocument, content: Tag, document: Document, covers: set[str]
    ) -> None:
        """Prepares a page's content for printing (also as part of a book).

        Inserts the title (when asked to) and cover pages, opens `<details>` and removes
        what must not be printed (permalinks, the theme's `removed` elements).
        """

        if self.options.title and document.title and content.find("h1") is None:
            heading = html.soup.new_tag("h1", attrs={"class": "mkdocs-exporter-title"})
            heading.string = document.title
            content.insert(0, heading)

        for location in COVER_LOCATIONS:
            if location in covers and location in document.covers:
                cover = html.fragment(
                    document.covers[location],
                    **{"class": f"mkdocs-exporter-{location}-cover"},
                )

                if location == "front":
                    content.insert(0, cover)
                else:
                    content.append(cover)

        html.set_attribute("details:not([open])", "open", "")
        html.remove([".headerlink", *self.theme.removed])

    def prepare(
        self, document: Document, keep: bool = False
    ) -> tuple[str, list[Heading], Prepared | None]:
        """The HTML to print for a document, its headings (outside of covers) and, when
        asked to `keep` it, its content prepared for books (see `Prepared`)."""

        html = HtmlDocument(document.html)
        content = self.theme.content_element(html)

        self.prepare_content(html, content, document, set(document.covers))
        html.mark_ancestors(content, ANCESTOR)

        # Without content element (the whole body), books parse the page again (see
        # `book.part_element`).
        keep = keep and content.name != "body"
        resources = (
            page_resources(html, content, document.url, self.site.prefix)
            if keep
            else None
        )
        moved = teleported(content) if keep else []
        headings = find_headings(content)
        contents = _insert_toc(html, content, headings, document.toc)

        _insert_anchors(html, headings)
        self._style(html, document)
        self._script(html)
        html.rewrite_links(
            lambda href: resolve_link(href, document.url, self.site.prefix, self._base)
        )

        output = str(html)

        if resources is None:
            return output, headings, None

        # Books reuse the content (without what they print themselves) instead of
        # parsing the page again.
        for _, _, element in moved:
            element.extract()
        if contents is not None:
            contents.extract()

        kept = Prepared(
            content=content.extract(), resources=resources, teleported=moved
        )

        return output, headings, kept

    @property
    def _base(self) -> str:
        """The URL links to the website start with, once resolved."""

        return self.options.links or RELATIVE_LINKS_BASE

    def _style(self, html: HtmlDocument, document: Document) -> None:
        """Adds the stylesheets of the exporter, the theme, headers and footers and the
        user to a document, then the styles teleported to the head (e.g. by covers),
        which take precedence over them."""

        hidden = [*self.theme.hidden, *self.options.hidden]
        stylesheets = [
            *self.base_stylesheets,
            self.options.margins.stylesheet(
                {**self.options.variables, "page_title": document.title},
                front_cover="front" in document.covers,
            ),
            *self.options.stylesheets,
        ]

        for stylesheet in stylesheets:
            if stylesheet:
                html.add_style(stylesheet)

        if hidden:
            html.add_style(", ".join(hidden) + " { display: none !important; }")

        html.teleport()

    def _script(self, html: HtmlDocument) -> None:
        """Adds the scripts of the exporter, the theme and the user to a document.

        The exporter's are the first scripts of the head (inserted in reverse order),
        so that errors are recorded from the start; the user's are the last of the body.
        """

        if theme_script := self.theme.print_script():
            html.add_script(theme_script, head=True, first=True)

        html.add_script(src=RESERVED + "pdf.js", head=True, first=True)
        html.add_data(
            "__MKDOCS_EXPORTER__", {"delay": self.options.delay}, head=True, first=True
        )

        for script in self.options.scripts:
            html.add_script(script)


def toc_entries(
    options: TocOptions | None,
    headings: Sequence[Heading],
    page: Callable[[str], int | None],
) -> list[toc.TocEntry]:
    """The entries of a document's table of contents (none without one)."""

    if options is None:
        return []

    return toc.heading_entries(toc.subheadings(headings), page, options.depth)


def _insert_toc(
    html: HtmlDocument,
    content: Tag,
    headings: Sequence[Heading],
    options: TocOptions | None,
) -> Tag | None:
    """Inserts a document's table of contents after its front cover, with
    placeholder page numbers (filled once printed, see `Refinement`)."""

    entries = toc_entries(options, headings, lambda _: 0)

    if options is None or not entries:
        return None

    return toc.insert(html, content, toc.render(options, entries))


def _insert_anchors(html: HtmlDocument, headings: Sequence[Heading]) -> None:
    """Inserts hidden links to every heading: browsers create named destinations for
    them, telling where headings land (and letting PDF readers link to them)."""

    if not headings:
        return

    anchors = html.soup.new_tag(
        "nav", attrs={"class": "mkdocs-exporter-anchors", "hidden": ""}
    )

    for heading in headings:
        anchors.append(html.soup.new_tag("a", attrs={"href": f"#{heading.id}"}))

    html.body.append(anchors)
