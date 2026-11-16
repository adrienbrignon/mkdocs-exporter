from __future__ import annotations

from collections.abc import Callable
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import Tag

from mkdocs_exporter.core.css import rewrite_urls as rewrite_css_urls
from mkdocs_exporter.core.html import ORIGIN, is_relative, resource_url

RESOURCES = {
    "src": (
        "audio",
        "embed",
        "iframe",
        "img",
        "input",
        "script",
        "source",
        "track",
        "video",
    ),
    "poster": ("video",),
    "data": ("object",),
    "action": ("form",),
}
"""Attributes holding the URL of a resource, by element."""

HYPERLINKS = ("a", "area")
"""Elements whose `href` is a link (the `href` of other elements is a resource)."""


def site_path(url: str, page_url: str, prefix: str) -> tuple[str, str] | None:
    """The path (relative to the website's root) and fragment a link leads to.

    `None` for anchors and links leaving the website. Root-absolute paths outside the
    prefix are relative to the website's root (like `resolve_link`).
    """

    if not is_relative(url):
        return None

    target = urlsplit(urljoin(ORIGIN + prefix + page_url, url.strip()))
    path = unquote(target.path)
    path = path[len(prefix) :] if path.startswith(prefix) else path.lstrip("/")

    if path.endswith("index.html"):
        path = path[: -len("index.html")]

    return path, unquote(target.fragment)


def _rewrite_srcset(srcset: str, rewrite: Callable[[str], str]) -> str:
    candidates = []

    for candidate in srcset.split(","):
        url, _, descriptor = candidate.strip().partition(" ")
        candidates.append(f"{rewrite(url)} {descriptor}".strip())

    return ", ".join(candidates)


def rewrite_urls(
    element: Tag,
    page_url: str,
    prefix: str,
    link: Callable[[str, str], str | None],
    base: str | None = None,
) -> None:
    """Makes the URLs found in an element valid wherever the element is served.

    Resources (`src`, `srcset`, `poster`, `data`, `action`, the `href` of `<link>`, SVG
    `href` and `xlink:href`, `url()` of `style` attributes and `<style>` elements) become
    root-absolute. Links (`<a>`, `<area>`) are given to `link` with the path (relative to
    the website's root) and fragment they lead to; it returns their new target (`None`
    keeps them as they are). Links starting with `base` (already resolved, see
    `resolve_link`) lead to the website's root followed by the rest of their URL.
    """

    def resource(url: str) -> str:
        return resource_url(url, page_url, prefix)

    for attribute, names in RESOURCES.items():
        for tag in element.find_all(names, attrs={attribute: True}):
            tag[attribute] = resource(str(tag[attribute]))
    for tag in element.find_all(["img", "source"], attrs={"srcset": True}):
        tag["srcset"] = _rewrite_srcset(str(tag["srcset"]), resource)
    for tag in element.find_all(True, attrs={"style": True}):
        if "url(" in str(tag["style"]):
            tag["style"] = rewrite_css_urls(str(tag["style"]), resource)
    for tag in element.find_all("style"):
        if tag.string and "url(" in tag.string:
            tag.string = rewrite_css_urls(tag.string, resource)
    for tag in element.find_all(True, attrs={"href": True}):
        href = str(tag["href"])

        if base and href.startswith(base):
            href = prefix + href[len(base) :]
        if tag.name not in HYPERLINKS:
            tag["href"] = resource(href)
        elif (target := site_path(href, page_url, prefix)) is not None and (
            rewritten := link(*target)
        ) is not None:
            tag["href"] = rewritten
    for tag in element.find_all(True, attrs={"xlink:href": True}):
        tag["xlink:href"] = resource(str(tag["xlink:href"]))
