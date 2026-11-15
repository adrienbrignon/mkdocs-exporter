from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from mkdocs_exporter.core import margins
from mkdocs_exporter.core.css import PageSelector, rename_pages, scope, split_page_rules

if TYPE_CHECKING:
    from mkdocs_exporter.core.books.assembly import Part

FRONT_COVER_PAGE = "mkdocs-exporter-front-cover"
"""The named page of front covers."""

BACK_COVER_PAGE = margins.COVER_PAGE
"""The named page of back covers (the same as in single documents)."""

CONTENT_PAGE = "mkdocs-exporter-content"
"""The named page of the parts' content, when they don't need one of their own."""

TOC_PAGE = "mkdocs-exporter-toc"
"""The named page of the table of contents."""

BLANK_PAGE = "mkdocs-exporter-blank"
"""The named page of blank pages (see `start: odd`)."""


@dataclass
class PageNames:
    """The named pages of a book's parts, by part identifier."""

    first: dict[str, str] = field(default_factory=dict)
    """The name of the first page of each part (its front cover's, its content's...)."""

    front: dict[str, str] = field(default_factory=dict)
    """The name of the pages of front covers."""

    content: dict[str, str] = field(default_factory=dict)
    """The name of the pages of each part's content."""


def translate_selector(
    selector: str, first: Sequence[str], every: Sequence[str], names: Mapping[str, str]
) -> list[str]:
    """Translates the selector of a `@page` rule written for a document of its own.

    Args:
        selector: The selector (e.g. `:first`, `cover:left`).
        first: The named pages `:first` stands for.
        every: The named pages a rule without page name applies to (none: unchanged).
        names: Page names to rename.

    Returns:
        The selectors of the rules to write (one per named page).
    """

    parsed = PageSelector.parse(selector)

    if parsed is None:
        return [selector]

    pseudos = "".join(f":{pseudo}" for pseudo in parsed.pseudos)

    if parsed.name:
        return [names.get(parsed.name, parsed.name) + pseudos]
    if "first" in parsed.pseudos:
        others = "".join(f":{pseudo}" for pseudo in parsed.pseudos if pseudo != "first")

        return [page + others for page in first]
    if every:
        return [page + pseudos for page in every]

    return [selector]


def translate_page_rules(
    stylesheet: str,
    first: Sequence[str],
    every: Sequence[str] = (),
    names: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """Translates the `@page` rules of a stylesheet (see `translate_selector`).

    Chromium's `:first` only matches the first page of the whole book, and doesn't
    support selector lists: each rule is written once per selector.

    Returns:
        The translated `@page` rules, and the rest of the stylesheet (with the `page`
        properties renamed according to `names`).
    """

    names = names or {}
    rules, rest = split_page_rules(stylesheet)
    pages = [
        f"@page {translated} {rule.block}"
        for rule in rules
        for selector in rule.selectors
        for translated in translate_selector(selector, first, every, names)
    ]

    return "\n".join(pages), rename_pages(rest, names) if names else rest


def page_names(stylesheet: str) -> set[str]:
    """The names of the pages a stylesheet defines `@page` rules for."""

    return {
        parsed.name
        for rule in split_page_rules(stylesheet)[0]
        for selector in rule.selectors
        if (parsed := PageSelector.parse(selector)) is not None and parsed.name
    }


def part_styles(parts: Sequence[Part]) -> tuple[list[str], PageNames]:
    """Translates the styles teleported to the head by the parts, and names their pages.

    Styles identical for every part teleporting some (the usual case: cover templates
    only use the website's variables in their styles) are included once, every front
    cover being on the `mkdocs-exporter-front-cover` page. Otherwise, every part gets
    pages of its own (`mkdocs-exporter-front-cover-N`, `mkdocs-exporter-part-N`), its
    `@page` rules are translated to them and its other rules scoped to the part.

    Returns:
        The stylesheets, and the names of the parts' pages (front covers and content;
        contents without a page of their own are left out).
    """

    names = PageNames()
    styled = [part for part in parts if part.styles]
    variants = {tuple(part.styles) for part in styled}

    if len(variants) <= 1:
        for part in parts:
            names.front[part.id] = FRONT_COVER_PAGE

        return [
            "\n".join(reversed(translate_page_rules(css, [FRONT_COVER_PAGE])))
            for css in next(iter(variants), ())
        ], names

    styles = []

    for part in parts:
        front = f"{FRONT_COVER_PAGE}-{part.index}"
        content = f"mkdocs-exporter-part-{part.index}"
        names.front[part.id] = front
        names.content[part.id] = content

        for stylesheet in part.styles:
            pages, rest = translate_page_rules(
                stylesheet,
                [front],
                [content, front],
                {name: f"{name}-{part.index}" for name in page_names(stylesheet)},
            )
            styles.append(scope(rest, f"#{part.id}") + "\n" + pages)

    return styles, names


def first_pages(css: str, parts: Sequence[Part], names: PageNames) -> str:
    """Translates the `@page :first` rules of a stylesheet applied to every page.

    In a page's own document, the first page is its front cover: in a book, `:first`
    would only match the book's first page. These rules apply to the pages of front
    covers instead (or to the book's first page when no part has a front cover).
    """

    covers = sorted({names.front[p.id] for p in parts if "front" in p.covers})

    if not covers or ":first" not in css:
        return css

    pages, rest = translate_page_rules(css, covers)

    return rest + "\n" + pages


def structure(
    parts: Sequence[Part],
    names: PageNames,
    toc: bool,
    titled: bool = False,
    back_covers: bool = False,
) -> str:
    """The stylesheet laying parts out on their pages.

    Each part starts on a new page; covers, the table of contents and blank pages are on
    named pages, as well as each part's content when headers or footers show its title
    (`titled`), and back covers when headers or footers are hidden there (`back_covers`,
    like in single documents). A change of named page starts a new page, even for an
    empty box: `body`
    and each part are given the name of their first page, and parts lose their
    pseudo-elements (e.g. Material's spacer), so that no page holds only empty boxes.
    """

    rules = [
        ".mkdocs-exporter-part + .mkdocs-exporter-part,"
        " .mkdocs-exporter-blank + .mkdocs-exporter-part { break-before: page; }",
        ".mkdocs-exporter-part::before, .mkdocs-exporter-part::after"
        " { content: none !important; }",
        f".mkdocs-exporter-blank {{ page: {BLANK_PAGE}; break-before: page;"
        " break-after: page; }",
        f".mkdocs-exporter-toc {{ page: {TOC_PAGE}; }}",
    ]

    for part in parts:
        front = names.front.get(part.id, FRONT_COVER_PAGE)
        content = names.content.get(
            part.id, f"mkdocs-exporter-part-{part.index}" if titled else CONTENT_PAGE
        )
        first = content

        if "front" in part.covers:
            first = front
        elif toc and part.index == 0:
            first = TOC_PAGE

        names.first[part.id] = first
        names.content.setdefault(part.id, content)
        names.front.setdefault(part.id, front)
        rules += [
            f"#{part.id} {{ page: {first}; }}",
            f":where(#{part.id}) > * {{ page: {content}; }}",
            f"#{part.id} > .mkdocs-exporter-front-cover {{ page: {front}; }}",
        ]

    if back_covers:
        rules.append(
            f".mkdocs-exporter-part > .mkdocs-exporter-back-cover"
            f" {{ page: {BACK_COVER_PAGE}; }}"
        )
    if parts:
        rules.append(f"body {{ page: {names.first[parts[0].id]}; }}")

    return "\n".join(rules) + "\n"
