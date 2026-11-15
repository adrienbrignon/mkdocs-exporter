from __future__ import annotations

import importlib.resources
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field

from jinja2 import Environment

CLASS = "mkdocs-exporter-toc"
"""The class of the element holding a table of contents."""

Heading = tuple[int, str, str]
"""A heading: (level, identifier, title)."""


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
        if heading[0] > depth:
            continue

        while stack and stack[-1][0] >= heading[0]:
            stack.pop()

        yield index, heading, stack[-1][1] if stack else -1
        stack.append((heading[0], index))


def subheadings(headings: Sequence[Heading]) -> list[Heading]:
    """Headings, without the document's title (its first heading, when it is a `h1`)."""

    return list(headings[1:] if headings and headings[0][0] == 1 else headings)


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

    for index, (_, id, title), parent in nested(headings, depth):
        if (number := page(id)) is None:
            continue

        entry = TocEntry(title=title, page=number, href="#" + id)
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
