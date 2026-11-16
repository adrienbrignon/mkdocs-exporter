from __future__ import annotations

from urllib.parse import unquote

from bs4 import Tag

from mkdocs_exporter.core.css import rename_selector_ids, rewrite_ids
from mkdocs_exporter.core.css import rewrite_urls as rewrite_css_urls

ID_ATTRIBUTES = ("for", "form", "list")
"""Attributes holding an identifier."""

ID_LIST_ATTRIBUTES = (
    "headers",
    "aria-activedescendant",
    "aria-controls",
    "aria-describedby",
    "aria-details",
    "aria-errormessage",
    "aria-flowto",
    "aria-labelledby",
    "aria-owns",
)
"""Attributes holding a space-separated list of identifiers."""

URL_REFERENCES = (
    "clip-path",
    "fill",
    "filter",
    "marker-end",
    "marker-mid",
    "marker-start",
    "mask",
    "stroke",
    "style",
)
"""Attributes that may reference an element with `url(#id)` (SVG, styles)."""


def collect_ids(element: Tag) -> set[str]:
    """The identifiers (and names of anchors and image maps) defined within an element."""

    ids = {str(tag["id"]) for tag in element.find_all(True, attrs={"id": True})}
    ids |= {
        str(tag["name"]) for tag in element.find_all(["a", "map"], attrs={"name": True})
    }

    return ids


def namespace_ids(element: Tag, prefix: str, ids: set[str]) -> None:
    """Prefixes the identifiers defined within an element, and every reference to them.

    Rewritten: `id`; the `name` of anchors, image maps and radio buttons (radio groups
    span the whole document: tabs of different parts sharing a group would uncheck each
    other); anchors in `href` and `xlink:href`; `for`, `form`, `list`, `headers`, `usemap`
    and ARIA references; `url(#id)` of SVG attributes, `style` attributes and `<style>`
    elements; `#id` selectors of `<style>` elements and `data-clipboard-target`.
    """

    def reference(value: str) -> str:
        return prefix + value if value in ids else value

    def anchor(href: str) -> str:
        if href.startswith("#") and unquote(href[1:]) in ids:
            return "#" + prefix + href[1:]

        return href

    for tag in element.find_all(True):
        attrs = tag.attrs

        if "id" in attrs:
            attrs["id"] = prefix + str(attrs["id"])
        if "name" in attrs and (
            tag.name in ("a", "map")
            or (tag.name == "input" and str(attrs.get("type", "")).lower() == "radio")
        ):
            attrs["name"] = prefix + str(attrs["name"])

        for key in ("href", "xlink:href", "usemap"):
            if key in attrs:
                attrs[key] = anchor(str(attrs[key]))
        for key in ID_ATTRIBUTES:
            if isinstance(value := attrs.get(key), str):
                attrs[key] = reference(value)
        for key in ID_LIST_ATTRIBUTES:
            if key in attrs:
                value = attrs[key]
                tokens = value if isinstance(value, list) else str(value).split()
                attrs[key] = " ".join(reference(token) for token in tokens)
        for key in URL_REFERENCES:
            if key in attrs and "url(" in str(attrs[key]):
                attrs[key] = rewrite_css_urls(str(attrs[key]), anchor)

        if "data-clipboard-target" in attrs:
            attrs["data-clipboard-target"] = rename_selector_ids(
                str(attrs["data-clipboard-target"]), reference
            )
        if tag.name == "style" and tag.string and "#" in tag.string:
            tag.string = rewrite_ids(tag.string, reference)
