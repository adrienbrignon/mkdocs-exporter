from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from mkdocs_exporter.logging import logger

ANCESTOR = "data-mkdocs-exporter-ancestor"
"""Marks the ancestors of a document's content (laid out as blocks in print)."""


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
                    "[mkdocs-exporter] Failed to teleport <%s> element: "
                    "destination '%s' not found",
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
