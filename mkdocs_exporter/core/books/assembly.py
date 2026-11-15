from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup, Comment, PageElement, Tag

from mkdocs_exporter.core import margins
from mkdocs_exporter.core.books.ids import collect_ids, namespace_ids
from mkdocs_exporter.core.books.styles import (
    BACK_COVER_PAGE,
    BLANK_PAGE,
    TOC_PAGE,
    PageNames,
    first_pages,
    part_styles,
    structure,
)
from mkdocs_exporter.core.books.urls import rewrite_urls
from mkdocs_exporter.core.document import Document, Heading
from mkdocs_exporter.core.html import (
    ANCESTOR,
    HtmlDocument,
    PageResources,
    page_resources,
    resolve_link,
)
from mkdocs_exporter.core.html import headings as find_headings
from mkdocs_exporter.core.toc import insert as insert_toc

if TYPE_CHECKING:
    from mkdocs_exporter.core.renderer import Prepared

PLACEHOLDER = "<!--mkdocs-exporter-parts-->"
"""Where the parts are inserted in the serialized shell (a comment)."""


@dataclass
class Part:
    """A page, as a part of a book."""

    index: int
    document: Document
    covers: set[str]
    """The covers kept."""

    html: HtmlDocument | None
    """The page, as parsed (the shell of the book, for the first part); `None` when the
    part reuses the content prepared for the page's own document (see `Prepared`)."""

    content: Tag
    """The page's content element (the part's element)."""

    resources: PageResources | None = None
    """The stylesheets and scripts of the page (read from `html` when missing)."""

    prepared: bool = False
    """Was the content already prepared for printing (covers, title...)?"""

    ids: set[str] = field(default_factory=set)
    """The identifiers defined by the part (before being namespaced)."""

    headings: list[Heading] = field(default_factory=list)
    """Its headings (with namespaced identifiers), outside of covers."""

    styles: list[str] = field(default_factory=list)
    """The styles it teleports to the head (e.g. its covers')."""

    teleported: list[Tag] = field(default_factory=list)
    """The other elements it teleports (to the shell)."""

    @property
    def id(self) -> str:
        """The identifier of the part's element."""

        return f"mkdocs-exporter-part-{self.index}"

    @property
    def prefix(self) -> str:
        """The prefix of the part's identifiers."""

        return f"p{self.index}-"

    @property
    def anchor(self) -> str:
        """Where links to the part lead: its first heading, or the part itself."""

        return self.headings[0].id if self.headings else self.id

    def keep(self, element: Tag, destination: str) -> None:
        """Keeps an element the part teleports: styles teleported to the head are
        translated with the book's (see `part_styles`), other elements are moved to
        the shell."""

        if destination == "head" and element.name == "style":
            self.styles.append(element.string or "")
        else:
            element["data-teleport"] = destination
            self.teleported.append(element)


@dataclass
class AssemblyOptions:
    """How pages are turned into a book."""

    prefix: str = "/"
    """The path under which the website is served (e.g. `/docs/`)."""

    links: str = "/"
    """The URL replacing the website's root in links to pages that aren't parts."""

    removed: Sequence[str] = ()
    """Selectors of elements removed from pages before printing."""

    hidden: Sequence[str] = ()
    """Selectors of elements hidden in the book."""

    head: Sequence[str] = ()
    """HTML inserted at the start of the head, in order (scripts that must run first)."""

    base_stylesheets: Sequence[str] = ()
    """Stylesheets of the exporter and the theme (before headers and footers)."""

    stylesheets: Sequence[str] = ()
    """Stylesheets of the user (after headers and footers, before teleported styles)."""

    scripts: Sequence[str] = ()
    """Scripts appended to the body."""

    margins: margins.Margins = field(default_factory=margins.Margins)
    """Headers and footers."""

    variables: Mapping[str, str] = field(default_factory=dict)
    """Values of the placeholders of headers and footers (e.g. `site_name`)."""

    toc_title: str = ""
    """The `{page_title}` of the pages of the table of contents."""


@dataclass
class Assembly:
    """An HTML document combining pages."""

    html: str
    parts: list[Part]
    pages: PageNames


def reuse(index: int, document: Document, covers: set[str], prepared: Prepared) -> Part:
    """A part made of a page's prepared content, keeping only some of its covers."""

    part = Part(
        index=index,
        document=document,
        covers=covers,
        html=None,
        content=prepared.content,
        resources=prepared.resources,
        prepared=True,
    )

    for location in ("front", "back"):
        if location not in covers:
            for cover in prepared.content.find_all(
                class_=f"mkdocs-exporter-{location}-cover", recursive=False
            ):
                cover.decompose()

    for origin, destination, element in prepared.teleported:
        if origin == "content" or origin in covers:
            part.keep(element, destination)

    return part


def part_element(html: HtmlDocument, content: Tag) -> Tag:
    """The element of a part: the page's content element.

    When the theme has none (the content being the whole `<body>`), the body's content is
    moved to a `<div>`, but its scripts: they are merged like other pages' scripts (see
    `page_resources`), instead of running again with each part.
    """

    if content.name != "body":
        return content

    element = html.soup.new_tag("div")

    for child in list(content.contents):
        if not (isinstance(child, Tag) and child.name == "script"):
            element.append(child.extract())

    content.insert(0, element)

    return element


def prepare(
    parts: Sequence[Part],
    options: AssemblyOptions,
    prepare_content: Callable[[Part], None] = lambda part: None,
) -> None:
    """Prepares the parts' content: teleported elements, identifiers, URLs and headings.

    Args:
        parts: The parts, whose `content` holds their kept covers.
        options: The options of the book.
        prepare_content: Adjusts a part's content first (e.g. opens `<details>`).
    """

    by_url: dict[str, Part] = {}

    for part in parts:
        if not part.prepared:
            prepare_content(part)

        by_url.setdefault(part.document.url, part)

        for element in part.content.select("[data-teleport]"):
            part.keep(element.extract(), str(element.get("data-teleport") or ""))

        found = find_headings(part.content, identify=True)
        part.ids = collect_ids(part.content)
        part.headings = [
            replace(heading, id=part.prefix + heading.id) for heading in found
        ]

    def link(path: str, fragment: str) -> str | None:
        """Links to parts lead within the book, other links to the website."""

        target = by_url.get(path)

        if target is not None:
            if fragment and fragment in target.ids:
                return "#" + target.prefix + fragment

            return "#" + target.anchor

        href = options.prefix + path + (f"#{fragment}" if fragment else "")

        return resolve_link(href, "", options.prefix, options.links)

    for part in parts:
        namespace_ids(part.content, part.prefix, part.ids)
        rewrite_urls(
            part.content, part.document.url, options.prefix, link, options.links
        )

        part.content["class"] = [  # type: ignore[assignment]
            *(part.content.get("class") or []),
            "mkdocs-exporter-part",
        ]
        part.content["id"] = part.id


@dataclass
class _Resources:
    """The stylesheets and scripts loaded by the book so far."""

    stylesheets: set[str] = field(default_factory=set)
    styles: set[str] = field(default_factory=set)
    scripts: set[str] = field(default_factory=set)
    head: list[str] = field(default_factory=list)
    """The HTML of the stylesheets and styles added to the shell's head."""
    body: list[str] = field(default_factory=list)
    """The HTML of the scripts added to the shell's body."""

    @classmethod
    def of(cls, parts: Sequence[Part], prefix: str) -> _Resources:
        """The stylesheets and scripts of the parts, those of the shell (the first
        part's page) excepted."""

        resources = cls()

        for part in parts:
            shell = part is parts[0]
            page = part.resources

            if page is None and part.html is not None:
                page = page_resources(
                    part.html, part.content, part.document.url, prefix, head=shell
                )

            resources.merge(page or PageResources(), shell)

        return resources

    def merge(self, page: PageResources, shell: bool = False) -> None:
        """Merges the stylesheets and scripts of a page into the book's.

        Stylesheets are deduplicated by URL, styles by content, scripts by URL,
        identifier or content (a page may load a script others don't, e.g. a diagram
        library). Those of the shell (the first page) are only registered.
        """

        for href in page.stylesheets:
            if href not in self.stylesheets and not shell:
                self.head.append(f'<link rel="stylesheet" href="{href}">')

            self.stylesheets.add(href)

        for text in page.styles:
            if text not in self.styles and not shell:
                self.head.append(f"<style>{text}</style>")

            self.styles.add(text)

        for key, html in page.scripts:
            if key not in self.scripts and not shell:
                self.body.append(html)

            self.scripts.add(key)


def _stylesheets(
    parts: Sequence[Part], options: AssemblyOptions, toc: bool
) -> tuple[list[str], PageNames]:
    """The stylesheets of a book, in order, and the names of its parts' pages."""

    styles, names = part_styles(parts)
    titled = options.margins.uses("page_title")
    names.complete(parts, toc, titled)
    titles = (
        {names.content[part.id]: part.document.title for part in parts}
        if titled
        else {}
    )
    css = [
        *options.base_stylesheets,
        options.margins.book_stylesheet(
            options.variables,
            {**titles, TOC_PAGE: options.toc_title},
            [*sorted(set(names.front.values())), BACK_COVER_PAGE],
            BLANK_PAGE,
        ),
        *(first_pages(css, parts, names) for css in options.stylesheets),
        structure(parts, names, back_covers=bool(options.margins.boxes)),
    ]

    if options.hidden:
        css.append(", ".join(options.hidden) + " { display: none !important; }")

    # Teleported styles last, so that they take precedence (like in single documents).
    return [*css, *styles], names


def _teleport(shell: HtmlDocument, parts: Sequence[Part]) -> None:
    """Moves the elements teleported by parts to the shell (unless their destination
    is missing)."""

    for element in (element for part in parts for element in part.teleported):
        selector = str(element.get("data-teleport") or "")
        destination = shell.select_one(selector) if selector else None

        if destination is not None:
            del element["data-teleport"]
            destination.append(element)


def _nodes(html: str) -> list[PageElement]:
    """The nodes of an HTML fragment, to insert one by one (BeautifulSoup 4.13.1 fails to
    insert an empty document)."""

    return list(BeautifulSoup(html, "html.parser").contents)


def assemble(
    parts: Sequence[Part], options: AssemblyOptions, toc: str | None
) -> Assembly:
    """Assembles prepared parts into a book (see `prepare`).

    The first part's page is the shell of the book: the parts replace its content, the
    stylesheets and scripts of other pages are added to it.

    Args:
        parts: The parts, in order.
        options: The options of the book.
        toc: The HTML of the table of contents, inserted after the first front cover.
    """

    first, shell = parts[0], parts[0].html

    if shell is None:
        raise ValueError("The first part of a book must hold its page")

    resources = _Resources.of(parts, options.prefix)

    if toc is not None:
        insert_toc(shell, first.content, toc)

    stylesheets, names = _stylesheets(parts, options, toc is not None)

    # Containers of the content are laid out as blocks in print (see `base.css`).
    shell.mark_ancestors(first.content, ANCESTOR)

    # Parts are serialized once, in place of the shell's content.
    content = "".join(str(part.content) for part in parts)
    first.content.replace_with(Comment(PLACEHOLDER[4:-3]))
    shell.remove(options.removed)
    shell.head.extend(_nodes("".join(resources.head)))

    for stylesheet in stylesheets:
        if stylesheet:
            shell.add_style(stylesheet)

    _teleport(shell, parts)

    for node in reversed(_nodes("".join(options.head))):
        shell.head.insert(0, node)

    shell.body.extend(_nodes("".join(resources.body)))

    for script in options.scripts:
        shell.add_script(script)

    return Assembly(
        html=str(shell).replace(PLACEHOLDER, content, 1),
        parts=list(parts),
        pages=names,
    )
