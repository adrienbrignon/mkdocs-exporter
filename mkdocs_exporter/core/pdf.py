"""PDF post-processing."""

from __future__ import annotations

import io
import posixpath

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject

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


def relativize_links(pdf: bytes, directory: str) -> bytes:
    """Turns links to the placeholder base into links relative to the document's directory."""

    reader = PdfReader(io.BytesIO(pdf))
    changed = False

    for page in reader.pages:
        for reference in page.get("/Annots") or []:
            action = reference.get_object().get("/A")

            if action is None:
                continue

            action = action.get_object()
            uri = str(action.get("/URI", ""))

            if uri.startswith(RELATIVE_LINKS_BASE):
                target = relative_url(uri[len(RELATIVE_LINKS_BASE) :], directory)
                action[NameObject("/URI")] = TextStringObject(target)
                changed = True

    if not changed:
        return pdf

    writer = PdfWriter(clone_from=reader)
    output = io.BytesIO()

    writer.write(output)

    return output.getvalue()
