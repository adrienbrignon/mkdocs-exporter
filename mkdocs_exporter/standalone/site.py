from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urljoin, urlsplit

from mkdocs.utils.meta import get_data
from mkdocs.utils.yaml import yaml_load

from mkdocs_exporter.core.books import NavNode
from mkdocs_exporter.logging import Logger
from mkdocs_exporter.standalone.project import Project, ProjectError

logger = Logger("pdf")

GENERATOR = re.compile(
    r"""<meta\s+name=["']generator["']\s+content=["']([^"']*)["']""", re.IGNORECASE
)
"""The generator of a built page (e.g. `zensical-0.1.1`)."""

LINK = re.compile(
    r"""<link\s+rel=["'](prev|next)["']\s+href=["']([^"']*)["']""", re.IGNORECASE
)
"""The links of a built page to the previous and next pages of the navigation."""

ORIGIN = "http://mkdocs-exporter.invalid/"
"""A placeholder origin to resolve the links between pages with."""


@dataclass
class Source:
    """The source file of a page."""

    src_uri: str
    """Its path, relative to the documentation directory."""


@dataclass
class BuiltPage:
    """A page of a built website."""

    file: Source
    url: str
    """Its URL, relative to the website's root (`guide/intro/`, or `guide/intro.html`)."""

    title: str | None
    path: Path
    """Its HTML file."""

    html: str
    meta: dict[str, Any] = field(default_factory=dict)
    """Its front matter (with the defaults of `.meta.yml` files)."""

    sections: list[str] = field(default_factory=list)
    """The titles of the navigation sections holding it, from the outermost."""

    @property
    def dest_uri(self) -> str:
        """Its HTML file, relative to the website's root."""

        return dest_uri(self.url)


def url_of(src_uri: str, use_directory_urls: bool) -> str:
    """The URL of the page built from a source file (like MkDocs and Zensical)."""

    path = PurePosixPath(src_uri)
    parent = "" if str(path.parent) == "." else f"{path.parent}/"

    if path.stem.lower() in ("index", "readme"):
        return parent if use_directory_urls else f"{parent}index.html"

    return (
        f"{parent}{path.stem}/" if use_directory_urls else f"{parent}{path.stem}.html"
    )


def dest_uri(url: str) -> str:
    """The HTML file of a page, relative to the website's root, from its URL."""

    return url + "index.html" if not url or url.endswith("/") else url


def generator(html: str) -> str | None:
    """The generator of a built page, as its `<meta name="generator">` tells."""

    match = GENERATOR.search(html)

    return match.group(1) if match else None


def pages(project: Project) -> list[BuiltPage]:
    """The pages of a built website that have a source file.

    Raises:
        ProjectError: When the website isn't built, or not by Zensical.
    """

    site_dir = project.site_dir

    if not (site_dir / "index.html").is_file():
        raise ProjectError(f"The website isn't built ('{site_dir}' has no home page)")

    sources = _sources(project)
    entries = _entries(project)
    found: list[BuiltPage] = []

    for url, (title, sections) in entries.items():
        src_uri = sources.pop(url, None)
        path = site_dir / dest_uri(url)

        if src_uri is None:
            logger.info("No source file for the built page '%s', skipped", url)
            continue
        if not path.is_file():
            logger.warning("The page '%s' isn't built ('%s' is missing)", url, path)
            continue

        found.append(
            BuiltPage(
                file=Source(src_uri),
                url=url,
                title=title,
                path=path,
                html=path.read_text(encoding="utf-8"),
                meta=_front_matter(project, src_uri),
                sections=sections,
            )
        )

    for url, src_uri in sources.items():
        logger.info("'%s' has no built page ('%s'), skipped", src_uri, url)

    _check_generator(found)

    return found


def navigation(project: Project, built: list[BuiltPage]) -> list[NavNode] | None:
    """The navigation of a website: its configuration's, else the one its pages
    follow (`<link rel="next">`); `None` when neither is known."""

    by_source = {page.file.src_uri: page for page in built}

    if project.nav is not None:
        return _configured(project.nav, by_source)

    chain = _chain(built)

    return _sectioned(chain) if chain else None


def documents(nav: list[NavNode]) -> list[str]:
    """The source files of a navigation's pages, in order."""

    return list(dict.fromkeys(key for node in nav for key in node.documents()))


def _sources(project: Project) -> dict[str, str]:
    """The source files of the website, by the URL of their page (`index.md` wins
    over `README.md`, like with MkDocs)."""

    docs_dir = project.docs_dir
    sources: dict[str, str] = {}

    for file in sorted(docs_dir.rglob("*.md")):
        relative = file.relative_to(docs_dir)

        if any(part.startswith(".") for part in relative.parts):
            continue

        src_uri = relative.as_posix()
        url = url_of(src_uri, project.use_directory_urls)

        if url not in sources or file.stem.lower() == "index":
            sources[url] = src_uri

    return sources


def _entries(project: Project) -> dict[str, tuple[str | None, list[str]]]:
    """The built pages, by URL: their title and the sections holding them, from the
    search index (else from the HTML files, without titles nor sections)."""

    index = project.site_dir / "search.json"

    if index.is_file():
        entries: dict[str, tuple[str | None, list[str]]] = {}

        for item in json.loads(index.read_text(encoding="utf-8")).get("items", []):
            location = str(item.get("location", ""))

            if "#" in location or location in entries:
                continue

            path = [str(title) for title in item.get("path") or []]
            entries[location] = (item.get("title"), path[:-1])

        return entries

    pattern = "index.html" if project.use_directory_urls else "*.html"

    return {
        _url(
            file.relative_to(project.site_dir).as_posix(), project.use_directory_urls
        ): (
            None,
            [],
        )
        for file in sorted(project.site_dir.rglob(pattern))
        if file.name != "404.html"
    }


def _url(dest_uri: str, use_directory_urls: bool) -> str:
    """The URL of a built page from its HTML file (`a/index.html` is `a/` with
    directory URLs)."""

    if use_directory_urls and (
        dest_uri == "index.html" or dest_uri.endswith("/index.html")
    ):
        return dest_uri[: -len("index.html")]

    return dest_uri


def _front_matter(project: Project, src_uri: str) -> dict[str, Any]:
    """The front matter of a source file, over the defaults of the `.meta.yml` files
    of its directories (when the `meta` plugin is enabled)."""

    path = project.docs_dir / src_uri
    _, meta = get_data(path.read_text(encoding="utf-8-sig"))
    meta_file = project.meta_file

    if meta_file is None:
        return meta

    defaults: dict[str, Any] = {}
    directory = project.docs_dir

    for part in ["", *PurePosixPath(src_uri).parent.parts]:
        directory = directory / part if part else directory
        file = directory / meta_file

        if file.is_file():
            with file.open(encoding="utf-8") as stream:
                data = yaml_load(stream) or {}

            if isinstance(data, Mapping):
                defaults = _merge(defaults, dict(data))

    return _merge(defaults, meta)


def _merge(base: dict[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Merges front matter like the `meta` plugin: mappings key by key, lists put
    together, other values replaced."""

    result = dict(base)

    for key, value in overrides.items():
        current = result.get(key)

        if isinstance(value, Mapping) and isinstance(current, Mapping):
            result[key] = _merge(dict(current), value)
        elif isinstance(value, list) and isinstance(current, list):
            result[key] = [*current, *value]
        else:
            result[key] = value

    return result


def _check_generator(built: list[BuiltPage]) -> None:
    """Refuses websites built by MkDocs or ProperDocs, whose plugin exports them."""

    name = next((g for page in built if (g := generator(page.html))), None)

    if name is None:
        logger.warning("Unknown generator of the website, assumed to be Zensical")
    elif name.lower().startswith("mkdocs") or "properdocs" in name.lower():
        raise ProjectError(
            f"The website was built by {name.split(',')[0]}: list the plugin in "
            "'plugins' instead, it exports documents while building the website"
        )


def _configured(nav: list[Any], pages: Mapping[str, BuiltPage]) -> list[NavNode]:
    """The navigation of the configuration (`nav`): file paths, mappings of titles to
    file paths or URLs, and of titles to sections."""

    nodes: list[NavNode] = []

    for item in nav:
        title, value = (
            next(iter(item.items())) if isinstance(item, Mapping) else (None, item)
        )

        if isinstance(value, list):
            nodes.append(
                NavNode(title=str(title or ""), children=_configured(value, pages))
            )
        elif isinstance(value, str) and not urlsplit(value).scheme:
            page = pages.get(PurePosixPath(value).as_posix().lstrip("/"))

            if page is not None:
                nodes.append(
                    NavNode(
                        title=str(title or page.title or ""),
                        document=page.file.src_uri,
                    )
                )

    return nodes


def _chain(built: list[BuiltPage]) -> list[BuiltPage]:
    """The pages in the order of their `<link rel="next">` (from the page without a
    previous one); empty when pages don't link to each other."""

    by_url = {page.url: page for page in built}
    links: dict[str, dict[str, str]] = {}

    for page in built:
        head = page.html[: page.html.find("</head>")]
        links[page.url] = {
            rel.lower(): _resolve(href, page.url) for rel, href in LINK.findall(head)
        }

    starts = [
        page
        for page in built
        if "next" in links[page.url] and "prev" not in links[page.url]
    ]

    if not starts:
        return []

    chain: list[BuiltPage] = []
    current: BuiltPage | None = starts[0]

    while current is not None and current not in chain:
        chain.append(current)
        current = by_url.get(links[current.url].get("next", "\0"))

    return chain


def _resolve(href: str, url: str) -> str:
    """The URL of a page, relative to the website's root, from a link of a page."""

    return unquote(urlsplit(urljoin(ORIGIN + url, href)).path).lstrip("/")


def _sectioned(chain: list[BuiltPage]) -> list[NavNode]:
    """A navigation tree from pages in order and the sections holding them."""

    nav: list[NavNode] = []

    for page in chain:
        nodes = nav

        for title in page.sections:
            section = nodes[-1] if nodes else None

            if (
                section is None
                or section.document is not None
                or section.title != title
            ):
                section = NavNode(title=title)
                nodes.append(section)

            nodes = section.children

        nodes.append(NavNode(title=page.title or "", document=page.file.src_uri))

    return nav
