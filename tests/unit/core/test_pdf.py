"""Tests of the PDF post-processing helpers."""

import pytest

from mkdocs_exporter.core.pdf import relative_url


@pytest.mark.parametrize(
    ("target", "directory", "expected"),
    [
        ("guide/intro/", "", "guide/intro/"),
        ("", "guide/intro", "../../"),
        ("", "", "./"),
        ("guide/advanced/#deep-dive", "guide/intro", "../advanced/#deep-dive"),
        ("guide/intro/", "guide/intro", "./"),
        ("index.html", "guide", "../index.html"),
        ("guide/intro.html?x=1", "guide", "intro.html?x=1"),
    ],
)
def test_relative_url(target: str, directory: str, expected: str) -> None:
    assert relative_url(target, directory) == expected


def test_set_metadata_appends_an_update() -> None:
    import io

    from pypdf import PdfReader, PdfWriter

    from mkdocs_exporter.core.pdf import set_metadata

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    output = io.BytesIO()
    writer.write(output)
    pdf = output.getvalue()

    updated = set_metadata(pdf, {"title": "Intro", "author": "Ada", "subject": ""})
    metadata = PdfReader(io.BytesIO(updated)).metadata or {}

    assert updated.startswith(pdf)
    assert metadata["/Title"] == "Intro"
    assert metadata["/Author"] == "Ada"
    assert "/Subject" not in metadata
    assert set_metadata(pdf, {}) == pdf
