from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from mkdocs_exporter.core.document import Heading
from mkdocs_exporter.logging import Logger

logger = Logger()

COVERS = ("mkdocs-exporter-front-cover", "mkdocs-exporter-back-cover")
"""The classes of cover pages."""

HEADING = re.compile(r"^h[1-6]$")

ANCESTOR = "data-mkdocs-exporter-ancestor"
"""Marks the ancestors of a document's content (laid out as blocks in print)."""

ORIGIN = "http://mkdocs-exporter.invalid"
"""A placeholder origin to resolve URLs with."""


class HtmlDocument:
    """An HTML document being prepared, either for the website or for printing."""

    def __init__(self, html: str) -> None:
        self.soup = BeautifulSoup(html, "lxml")

    def __str__(self) -> str:
        return str(self.soup)

    @property
    def head(self) -> Tag:
        """The document's `<head>` (created when missing)."""

        if self.soup.head is None:
            self._root().insert(0, self.soup.new_tag("head"))

        return self.soup.head  # type: ignore[return-value]

    @property
    def body(self) -> Tag:
        """The document's `<body>` (created when missing)."""

        if self.soup.body is None:
            self._root().append(self.soup.new_tag("body"))

        return self.soup.body  # type: ignore[return-value]

    def fragment(self, html: str, **attributes: str) -> Tag:
        """Creates a `<div>` element holding an HTML fragment."""

        element = self.soup.new_tag("div", attrs=attributes)

        for node in list(BeautifulSoup(html, "html.parser").contents):
            element.append(node.extract())

        return element

    def select(self, selector: str) -> list[Tag]:
        """Selects elements with a CSS selector."""

        return list(self.soup.select(selector))

    def select_one(self, selector: str) -> Tag | None:
        """Selects the first element matching a CSS selector."""

        return self.soup.select_one(selector)

    def remove(self, selectors: str | Iterable[str]) -> HtmlDocument:
        """Removes the elements matching some CSS selectors."""

        for selector in [selectors] if isinstance(selectors, str) else selectors:
            for element in self.soup.select(selector):
                element.decompose()

        return self

    def set_attribute(self, selector: str, key: str, value: str) -> HtmlDocument:
        """Sets an attribute on the elements matching a CSS selector."""

        for element in self.soup.select(selector):
            element[key] = value

        return self

    def teleport(self) -> HtmlDocument:
        """Moves elements having a `data-teleport` attribute to their destination."""

        for element in self.soup.select("[data-teleport]"):
            selector = str(element.get("data-teleport") or "")
            destination = self.soup.select_one(selector) if selector else None

            if destination is None:
                logger.warning(
                    "Failed to teleport <%s> element: destination '%s' not found",
                    element.name,
                    selector,
                )
                continue

            del element["data-teleport"]
            destination.append(element.extract())

        return self

    def mark_ancestors(self, element: Tag, attribute: str) -> HtmlDocument:
        """Sets an (empty) attribute on the ancestors of an element, up to the body."""

        for ancestor in element.parents:
            if ancestor.name in ("html", "[document]"):
                break

            ancestor[attribute] = ""

        return self

    def add_style(self, css: str, **attributes: str) -> HtmlDocument:
        """Appends a stylesheet to the document's head."""

        element = self.soup.new_tag("style", attrs=attributes)
        element.string = css

        self.head.append(element)

        return self

    def add_script(
        self,
        content: str | None = None,
        src: str | None = None,
        head: bool = False,
        first: bool = False,
        **attributes: str,
    ) -> HtmlDocument:
        """Appends a script to the document's body (or head, optionally first)."""

        element = self.soup.new_tag("script", attrs=attributes)

        if src is not None:
            element["src"] = src
        if content is not None:
            element.string = content

        parent = self.head if head else self.body

        if first:
            parent.insert(0, element)
        else:
            parent.append(element)

        return self

    def add_data(
        self, name: str, value: Any, head: bool = False, first: bool = False
    ) -> HtmlDocument:
        """Exposes some JSON-serializable data as a global JavaScript variable."""

        payload = json.dumps(value).replace("</", "<\\/")

        return self.add_script(f"window.{name} = {payload};", head=head, first=first)

    def rewrite_links(self, rewrite: Callable[[str], str | None]) -> HtmlDocument:
        """Rewrites the `href` of anchors (`None` keeps a link untouched)."""

        for element in self.soup.select("a[href]"):
            href = rewrite(str(element["href"]))

            if href is not None:
                element["href"] = href

        return self

    def _root(self) -> Tag:
        return self.soup.html or self.soup


def resolve_link(href: str, page_url: str, prefix: str, base: str) -> str | None:
    """Resolves a link found in a page to a URL usable from a PDF document.

    Args:
        href: The link's target, as found in the page.
        page_url: The URL of the page, relative to the website's root.
        prefix: The path under which the website is served (e.g. `/docs/`).
        base: The URL that replaces the website's root (e.g. `https://example.org/docs/`).

    Returns:
        The rewritten link, or `None` when it must be left untouched (anchors within the
        page, external links and non-HTTP schemes such as `mailto:`).
    """

    if not href or href.startswith("#"):
        return None

    parts = urlsplit(href)

    if parts.scheme or parts.netloc:
        return None

    origin = "http://mkdocs-exporter.invalid"
    target = urlsplit(urljoin(origin + prefix + page_url, href))
    path = target.path

    path = path[len(prefix) :] if path.startswith(prefix) else path.lstrip("/")

    return urlunsplit(
        urlsplit(urljoin(base, path))._replace(
            query=target.query, fragment=target.fragment
        )
    )


def headings(content: Tag, identify: bool = False) -> list[Heading]:
    """The headings of a page's content, outside of its covers.

    Args:
        content: The content.
        identify: Should headings without identifier be given one (instead of being left
            out)?
    """

    found = []

    for index, tag in enumerate(content.find_all(HEADING)):
        if tag.find_parent(class_=COVERS) is not None:
            continue
        if not tag.get("id"):
            if not identify:
                continue

            tag["id"] = f"mkdocs-exporter-heading-{index}"

        title = "".join(
            text
            for text in tag.find_all(string=True)
            if text.find_parent(class_="headerlink") is None
        )
        found.append(Heading(int(tag.name[1]), str(tag["id"]), " ".join(title.split())))

    return found


def is_relative(url: str) -> bool:
    """Is a URL relative to the page (neither absolute, nor an anchor, nor `data:`...)?"""

    url = url.strip()

    return bool(url) and not url.startswith(("#", "//")) and not urlsplit(url).scheme


def resource_url(url: str, page_url: str, prefix: str) -> str:
    """Resolves the URL of a resource found in a page as a root-absolute URL.

    `../img/logo.png` found in `guide/intro/` becomes `<prefix>guide/img/logo.png`. URLs
    that are already root-absolute are kept: the server resolves them against the
    website's prefix, then against its root.
    """

    if not is_relative(url) or url.startswith("/"):
        return url

    target = urlsplit(urljoin(ORIGIN + prefix + page_url, url.strip()))

    return urlunsplit(("", "", target.path, target.query, target.fragment))


def within(tag: Tag, ancestor: Tag) -> bool:
    """Is a tag a descendant of another (by identity: `Tag.__eq__` compares markup)?"""

    return any(parent is ancestor for parent in tag.parents)


def teleported(content: Tag) -> list[tuple[str, str, Tag]]:
    """The elements a page's content teleports (see `Prepared.teleported`)."""

    found = []

    for element in content.find_all(True, attrs={"data-teleport": True}):
        origin = "content"

        for location in ("front", "back"):
            cover = element.find_parent(class_=f"mkdocs-exporter-{location}-cover")

            if cover is not None and cover.parent is content:
                origin = location

        found.append((origin, str(element.get("data-teleport") or ""), element))

    return found


@dataclass
class PageResources:
    """The stylesheets and scripts a page loads (outside of its content)."""

    stylesheets: list[str] = field(default_factory=list)
    """The (root-absolute) URLs of stylesheets."""

    styles: list[str] = field(default_factory=list)
    """The contents of `<style>` elements."""

    scripts: list[tuple[str, str]] = field(default_factory=list)
    """The scripts of the body: (key, HTML), the key identifying the script by URL,
    identifier or content."""


def page_resources(
    html: HtmlDocument, content: Tag, page_url: str, prefix: str, head: bool = False
) -> PageResources:
    """The stylesheets and scripts of a page, outside of its content.

    Scripts of the head are left out, unless `head` is set: they usually configure their
    own page.
    """

    resources = PageResources()
    document_head = html.soup.head

    for tag in html.soup.find_all(["link", "style", "script"]):
        if tag.name == "link":
            if tag.get("href") and "stylesheet" in (tag.get("rel") or []):
                href = resource_url(str(tag["href"]), page_url, prefix)
                resources.stylesheets.append(href)
            continue
        if within(tag, content):
            continue
        if tag.name == "style":
            if tag.string:
                resources.styles.append(tag.string)
            continue
        if not head and document_head is not None and within(tag, document_head):
            continue

        if tag.get("src"):
            tag = copy.copy(tag)
            tag["src"] = resource_url(str(tag["src"]), page_url, prefix)
            key = "src:" + str(tag["src"])
        elif tag.get("id"):
            key = "id:" + str(tag["id"])
        else:
            key = "text:" + (tag.string or "")

        resources.scripts.append((key, str(tag)))

    return resources
