"""PDF post-processing."""

from __future__ import annotations

import io
import posixpath
from collections.abc import Callable
from typing import cast

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

RELATIVE_LINKS_BASE = "https://mkdocs-exporter.invalid/"
"""A placeholder base URL for links that must end up relative to the PDF document."""


def relative_url(target: str, directory: str) -> str:
    """Returns a URL relative to the website's root as a URL relative to a directory."""

    path, _, fragment = target.partition("#")
    path, _, query = path.partition("?")
    relative = (
        posixpath.relpath("/" + path, "/" + directory) if path or directory else "."
    )

    if path.endswith("/") or not path:
        relative = relative.rstrip("/") + "/"
    if relative.startswith("./"):
        relative = relative[2:] or "./"

    return (
        relative + (f"?{query}" if query else "") + (f"#{fragment}" if fragment else "")
    )


def link_actions(writer: PdfWriter) -> list[tuple[int, DictionaryObject, str]]:
    """The URI link annotations of a document: (page index, annotation, URI)."""

    links = []

    for index, page in enumerate(writer.pages):
        for reference in page.get("/Annots") or []:
            annotation = reference.get_object()
            action = annotation.get("/A")

            if action is None:
                continue

            uri = action.get_object().get("/URI")

            if uri is not None:
                links.append((index, annotation, str(uri)))

    return links


def rewrite_links(pdf: bytes, rewrite: Callable[[str], str | None]) -> bytes:
    """Rewrites the URIs of a document's links (`None` keeps a link untouched)."""

    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    changed = False

    for _, annotation, uri in link_actions(writer):
        target = rewrite(uri)

        if target is not None and target != uri:
            action = cast(DictionaryObject, annotation["/A"].get_object())
            action[NameObject("/URI")] = TextStringObject(target)
            changed = True

    if not changed:
        return pdf

    output = io.BytesIO()

    writer.write(output)

    return output.getvalue()
