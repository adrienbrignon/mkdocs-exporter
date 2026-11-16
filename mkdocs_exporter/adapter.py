from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from fnmatch import fnmatchcase
from typing import Any

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.nav import Section
from mkdocs.structure.pages import Page

from mkdocs_exporter.core.books import Book, NavNode
from mkdocs_exporter.core.browser import Browser
from mkdocs_exporter.core.document import Document
from mkdocs_exporter.core.margins import Margins
from mkdocs_exporter.core.renderer import RenderOptions
from mkdocs_exporter.core.toc import TocOptions
from mkdocs_exporter.formats.pdf.config import (
    BookConfig,
    BrowserConfig,
    TocConfig,
)
from mkdocs_exporter.formats.pdf.config import Config as PdfConfig


def render_options(options: PdfConfig, config: MkDocsConfig) -> RenderOptions:
    """The options of the renderer."""

    links = options.url or config.site_url or None

    return RenderOptions(
        stylesheets=[read(path) for path in options.stylesheets],
        scripts=[read(path) for path in options.scripts],
        links=links if links is None or links.endswith("/") else links + "/",
        delay=options.browser.delay,
        concurrency=options.concurrency,
        title=options.title,
        margins=Margins.of(
            {"header": dict(options.header), "footer": dict(options.footer)}
        ),
        variables={"site_name": config.site_name},
    )


def browser(options: BrowserConfig) -> Browser:
    """The browser printing documents (not launched)."""

    return Browser(
        headless=options.headless,
        timeout=options.timeout,
        args=options.args,
        channel=options.channel,
        debug=options.debug,
    )


def document(
    page: Page,
    html: str,
    path: str,
    covers: Mapping[str, str],
    options: PdfConfig,
    config: MkDocsConfig,
) -> Document:
    """The document of a page.

    Args:
        page: The page.
        html: Its HTML.
        path: The location of its document, relative to the website's root.
        covers: Its rendered cover pages, by location.
        options: The options of PDF documents.
        config: The configuration of the website.
    """

    return Document(
        id=page.file.src_uri,
        url=page.url,
        path=path,
        title=page.title or "",
        html=html,
        meta=dict(page.meta),
        covers=dict(covers),
        metadata=metadata(page, config),
        toc=toc(options.toc, bool(page.meta.get("toc", options.toc.enabled))),
    )


def metadata(page: Page, config: MkDocsConfig) -> dict[str, str]:
    """The document information of a page's document."""

    keywords = page.meta.get("keywords") or page.meta.get("tags") or []

    if isinstance(keywords, str):
        keywords = [keywords]

    return {
        key: str(value)
        for key, value in {
            "title": page.title,
            "author": page.meta.get("author") or config.site_author,
            "subject": page.meta.get("description") or config.site_description,
            "keywords": ", ".join(str(keyword) for keyword in keywords),
        }.items()
        if value
    }


def navigation(items: Sequence[Any]) -> list[NavNode]:
    """The navigation of the website (pages and sections, in order)."""

    nodes: list[NavNode] = []

    for item in items:
        if isinstance(item, Page) and item.file is not None:
            nodes.append(NavNode(title=item.title or "", document=item.file.src_uri))
        elif isinstance(item, Section):
            nodes.append(NavNode(title=item.title, children=navigation(item.children)))

    return nodes


def books(options: PdfConfig) -> list[BookConfig]:
    """The enabled books (including the deprecated `aggregator`)."""

    return [book for book in [*options.books, options.aggregator] if book.enabled]


def book(
    options: BookConfig,
    config: MkDocsConfig,
    documents: Sequence[Document],
    nav: Sequence[NavNode],
) -> Book:
    """A book of documents (see `includes`)."""

    return Book(
        output=output(options),
        documents=documents,
        covers=options.covers,
        start=options.start,
        metadata={
            "title": config.site_name,
            "author": config.site_author,
            "subject": config.site_description,
            **options.metadata,
        },
        nav=nav,
        outline=options.outline,
        toc=toc(options.toc),
    )


def includes(options: BookConfig, key: str) -> bool:
    """Does a book include a page (by source path)?"""

    return any(fnmatchcase(key, pattern) for pattern in options.include) and not any(
        fnmatchcase(key, pattern) for pattern in options.exclude
    )


def output(options: BookConfig) -> str:
    """The location of a book, relative to the website's root."""

    return options.output.replace(os.sep, "/").lstrip("/")


def title(options: BookConfig, config: MkDocsConfig) -> str:
    """The title of a book (the website's name by default)."""

    return str(options.metadata.get("title") or config.site_name)


def toc(options: TocConfig, enabled: bool | None = None) -> TocOptions | None:
    """The options of a table of contents (`None` when it is disabled).

    Args:
        options: Its configuration.
        enabled: Overrides `options.enabled` (e.g. from a page's front matter).
    """

    if not (options.enabled if enabled is None else enabled):
        return None

    return TocOptions(
        title=options.title,
        depth=options.depth,
        template=read(options.template) if options.template else None,
    )


def read(path: str) -> str:
    """Reads a text file."""

    with open(path, encoding="utf-8") as file:
        return file.read()
