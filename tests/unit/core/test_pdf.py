import io
import logging

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    StreamObject,
)

from mkdocs_exporter.core.pdf import clone, info, relative_url, serialize


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


def shared_profile(images: int) -> bytes:
    """A document whose images share a color profile (like Chromium prints them)."""

    writer = PdfWriter()
    profile = StreamObject()
    profile.set_data(b"profile")
    profile[NameObject("/N")] = NumberObject(3)
    reference = writer._add_object(profile)

    for index in range(images):
        image = StreamObject()
        image.set_data(b"\x00\x00\x00")
        image.update(
            {
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Image"),
                NameObject("/Width"): NumberObject(1),
                NameObject("/Height"): NumberObject(1),
                NameObject("/BitsPerComponent"): NumberObject(8),
                NameObject("/ColorSpace"): ArrayObject(
                    [NameObject("/ICCBased"), reference]
                ),
            }
        )
        page = writer.add_blank_page(100, 100)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/XObject"): DictionaryObject(
                    {NameObject(f"/Im{index}"): writer._add_object(image)}
                )
            }
        )

    output = io.BytesIO()
    writer.write(output)

    return output.getvalue()


def profiles(pdf: bytes) -> int:
    reader = PdfReader(io.BytesIO(pdf))

    return sum(
        isinstance(obj := reader.get_object(number), StreamObject)
        and obj.get("/N") == 3
        for number in reader.xref[0]
    )


def test_copies_of_documents_merge_the_objects_pypdf_duplicates(
    caplog: pytest.LogCaptureFixture,
) -> None:
    pdf = shared_profile(5)
    caplog.set_level(logging.WARNING, logger="pypdf")

    PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))

    assert "exceeds defined trailer size" in caplog.text

    caplog.clear()
    writer = clone(pdf)
    copy = serialize(writer)

    assert caplog.text == ""
    assert len(writer._objects) > PdfReader(io.BytesIO(pdf)).trailer["/Size"]
    assert profiles(pdf) == 1
    assert profiles(copy) == 1


def test_document_information_lists_are_joined() -> None:
    assert info({"title": "T", "keywords": ["a", "b"], "author": None, "/X": 1}) == {
        "/Title": "T",
        "/Keywords": "a, b",
        "/X": "1",
    }
