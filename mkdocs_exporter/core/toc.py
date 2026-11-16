from __future__ import annotations

import importlib.resources
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field

from bs4 import Tag
from jinja2 import Environment

from mkdocs_exporter.core.document import Heading
from mkdocs_exporter.core.html import HtmlDocument

CLASS = "mkdocs-exporter-toc"
"""The class of the element holding a table of contents."""


@dataclass
class TocOptions:
    """Options of a table of contents."""

    title: str = "Table of contents"

    depth: int = 2
    """The deepest level of headings listed (`h2` by default); in combined documents,
    1 lists the pages only."""

    template: str | None = None
    """A Jinja template replacing the default one."""


@dataclass
class TocEntry:
    """An entry of a table of contents."""

    title: str
    page: int
    href: str
    children: list[TocEntry] = field(default_factory=list)


def nested(
    headings: Sequence[Heading], depth: int
) -> Iterator[tuple[int, Heading, int]]:
    """Headings up to a level: (index, heading, index of the parent heading or -1)."""

    stack: list[tuple[int, int]] = []

    for index, heading in enumerate(headings):
        if heading.level > depth:
            continue

        while stack and stack[-1][0] >= heading.level:
            stack.pop()

        yield index, heading, stack[-1][1] if stack else -1
        stack.append((heading.level, index))


def subheadings(headings: Sequence[Heading]) -> list[Heading]:
    """Headings, without the document's title (its first heading, when it is a `h1`)."""

    return list(headings[1:] if headings and headings[0].level == 1 else headings)


def heading_entries(
    headings: Sequence[Heading], page: Callable[[str], int | None], depth: int
) -> list[TocEntry]:
    """The entries of headings up to a level, nested by level.

    Args:
        headings: The headings, in order.
        page: The page number of a heading's identifier (`None` when it isn't printed:
            the heading is left out, its children taking its place).
        depth: The deepest level of headings listed.
    """

    entries: list[TocEntry] = []
    created: dict[int, TocEntry] = {}

    for index, heading, parent in nested(headings, depth):
        if (number := page(heading.id)) is None:
            continue

        entry = TocEntry(title=heading.title, page=number, href="#" + heading.id)
        created[index] = entry
        (created[parent].children if parent in created else entries).append(entry)

    return entries


def render(options: TocOptions, entries: Sequence[TocEntry]) -> str:
    """Renders a table of contents (HTML)."""

    from mkdocs_exporter.core import resources

    source = options.template or (
        importlib.resources.files(resources)
        .joinpath("toc.html")
        .read_text(encoding="utf-8")
    )

    return (
        Environment(autoescape=True)
        .from_string(source)
        .render(title=options.title, entries=entries)
    )


def insert(html: HtmlDocument, content: Tag, markup: str) -> Tag:
    """Inserts a table of contents (its HTML) at the start of a document's content,
    after its front cover."""

    element = html.fragment(markup, **{"class": CLASS})
    covers = content.find_all(class_="mkdocs-exporter-front-cover", recursive=False)

    if covers:
        covers[0].insert_after(element)
    else:
        content.insert(0, element)

    return element
