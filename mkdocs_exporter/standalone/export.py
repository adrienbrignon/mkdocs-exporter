from __future__ import annotations

import posixpath

from mkdocs_exporter import adapter, front_matter
from mkdocs_exporter.core.books import Book
from mkdocs_exporter.core.books.outline import flat_nav
from mkdocs_exporter.core.cache import Cache
from mkdocs_exporter.core.document import Document, Site
from mkdocs_exporter.core.exporter import Exporter, Report
from mkdocs_exporter.core.html import LEGACY_TELEPORT, TELEPORT, HtmlDocument
from mkdocs_exporter.core.renderer import Outcome
from mkdocs_exporter.core.runner import run
from mkdocs_exporter.core.themes import get_theme
from mkdocs_exporter.covers import CoverRenderer
from mkdocs_exporter.logging import Logger
from mkdocs_exporter.standalone import site
from mkdocs_exporter.standalone.project import Project, ProjectError
from mkdocs_exporter.standalone.site import BuiltPage

logger = Logger("pdf")

EXPORTED = "mkdocs-exporter"
"""The name of the `<meta>` element marking the pages rewritten after an export."""

MARKERS = ("mkdocs-exporter-only", "data-decompose", TELEPORT, LEGACY_TELEPORT)
"""What the pages of the website are rewritten for."""


def export(project: Project) -> list[Outcome]:
    """Exports a website built by Zensical: the documents of its pages and its books,
    then removes what is meant for documents only from its pages.

    Returns:
        The documents that could not be rendered.

    Raises:
        ProjectError: When the website can't be exported.
    """

    options = project.options.formats.pdf

    if not options.enabled:
        logger.info("PDF documents are disabled ('formats.pdf.enabled')")
        return []

    _warn_ignored(project)

    built = site.pages(project)

    if any(f'<meta name="{EXPORTED}"' in page.html for page in built):
        raise ProjectError(
            "The website was already exported (its pages lost what is meant for "
            "documents only): build it again first"
        )

    nav = site.navigation(project, built)
    order = site.documents(nav) if nav is not None else [p.file.src_uri for p in built]
    exports = _documents(project, built)

    if not exports:
        logger.warning("No page to export")
        return []

    listed = set(order)
    documents = [exports[key] for key in order if key in exports]
    documents += [document for key, document in exports.items() if key not in listed]
    report = run(
        lambda: _export(project, documents, _books(project, exports, order, nav))
    )

    if not report.failures:
        _rewrite(built)

    return report.failures


def _documents(project: Project, built: list[BuiltPage]) -> dict[str, Document]:
    """The documents of the pages, by source file."""

    options = project.options.formats.pdf
    website = project.website
    covers = CoverRenderer(str(project.root), website.extra, project.settings)
    deprecated: set[str] = set()
    documents: dict[str, Document] = {}

    for page in built:
        key = page.file.src_uri

        try:
            parsed = front_matter.parse(page.meta)
        except front_matter.FrontMatterError as error:
            raise ProjectError(f"Invalid front matter in '{key}': {error}") from error

        for name in parsed.deprecated:
            _deprecated(
                deprecated,
                f"'{'hide: [covers]' if name == 'hide' else name}' key of the "
                "front matter",
                key,
                front_matter.DEPRECATED[name],
            )

        if parsed.options.buttons and "buttons" not in deprecated:
            deprecated.add("buttons")
            logger.warning(
                "Buttons aren't added to the pages of the website ('exporter.buttons' "
                "of '%s')",
                key,
            )

        enabled = parsed.options.pdf.enabled

        if not (not options.explicit if enabled is None else enabled):
            continue

        templates = covers.locations(dict(options.covers), parsed.options.pdf.covers)
        documents[key] = adapter.document(
            page,
            page.html,
            posixpath.splitext(page.dest_uri)[0] + ".pdf",
            {
                location: covers.render(path, page)
                for location, path in templates.items()
            },
            options,
            website,
            parsed.options,
        )

    return documents


def _books(
    project: Project,
    exports: dict[str, Document],
    order: list[str],
    nav: list | None,
) -> list[Book]:
    """The books of the website, of the documents of the pages of its navigation."""

    books = []

    for options in adapter.books(project.options.formats.pdf):
        documents = [
            exports[key]
            for key in order
            if key in exports and adapter.includes(options, key)
        ]
        books.append(
            adapter.book(
                options,
                project.website,
                documents,
                nav if nav is not None else flat_nav(documents),
            )
        )

    return books


async def _export(
    project: Project, documents: list[Document], books: list[Book]
) -> Report:
    """Renders the documents and the books."""

    options = project.options.formats.pdf
    cache = None

    if options.cache.enabled:
        cache = Cache(project.root / options.cache.directory)

    theme = project.options.theme
    exporter = Exporter(
        Site(directory=project.site_dir, url=project.website.url),
        get_theme(theme.name if theme else "material"),
        adapter.browser(options.browser),
        adapter.render_options(options, project.website),
        cache,
    )
    report = await exporter.export(documents, books)

    if cache is not None and not report.failures:
        cache.prune()

    return report


def _rewrite(built: list[BuiltPage]) -> None:
    """Removes what is meant for documents only from the pages of the website, and
    moves the elements to teleport (like the plugin does while building pages)."""

    deprecated: set[str] = set()

    for page in built:
        if not any(marker in page.html for marker in MARKERS):
            continue

        html = HtmlDocument(page.html)
        key = page.file.src_uri

        if html.legacy_teleports:
            _deprecated(deprecated, "'data-teleport' attribute", key, f"'{TELEPORT}'")
        if html.select('[data-decompose="true"]'):
            _deprecated(
                deprecated,
                "'data-decompose=\"true\"' attribute",
                key,
                "the 'mkdocs-exporter-only' class",
            )

        html.remove([".mkdocs-exporter-only", '[data-decompose="true"]'])
        html.teleport()
        html.head.append(html.soup.new_tag("meta", attrs={"name": EXPORTED}))
        page.path.write_text(str(html), encoding="utf-8")


def _deprecated(warned: set[str], feature: str, where: str, replacement: str) -> None:
    """Warns about a deprecated feature (once)."""

    if feature not in warned:
        warned.add(feature)
        logger.warning(
            "The %s is deprecated (used in '%s'), use %s instead",
            feature,
            where,
            replacement,
        )


def _warn_ignored(project: Project) -> None:
    """Warns about the options the command doesn't support."""

    options = project.options

    if "buttons" in project.ignored:
        logger.warning("Buttons aren't added to the pages of the website ('buttons')")
    if options.formats.pdf.serve:
        logger.warning("Websites being served aren't exported ('formats.pdf.serve')")
