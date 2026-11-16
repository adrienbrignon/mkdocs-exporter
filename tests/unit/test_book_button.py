from types import SimpleNamespace
from typing import Any

import pytest

from mkdocs_exporter.formats.pdf.buttons import book


def page(url: str, *books: str, pdf: bool = True) -> SimpleNamespace:
    """A minimal stand-in for a MkDocs page, part of books (by URL)."""

    entries: list[dict[str, Any]] = [
        {"url": output, "path": "/site/" + output, "title": f"Book {index}"}
        for index, output in enumerate(books, 1)
    ]
    formats = {"pdf": {"url": "index.pdf", "books": entries}} if pdf else {}

    return SimpleNamespace(url=url, title="Intro", meta={}, formats=formats)


@pytest.mark.parametrize(
    ("url", "output", "expected"),
    [
        ("", "book.pdf", "book.pdf"),
        ("guide/intro/", "book.pdf", "../../book.pdf"),
        ("guide/intro.html", "pdf/guide.pdf", "../pdf/guide.pdf"),
    ],
)
def test_href_is_relative_to_the_page(url: str, output: str, expected: str) -> None:
    assert book.href(page(url, output)) == expected


def test_links_to_the_first_book_of_the_page() -> None:
    assert book.attributes(page("", "guide.pdf", "all.pdf")) == {
        "href": "guide.pdf",
        "download": "Book 1.pdf",
    }


def test_enabled_only_when_the_page_is_part_of_a_book() -> None:
    assert book.enabled(page("", "book.pdf")) is True
    assert book.enabled(page("")) is False
    assert book.enabled(page("", "book.pdf", pdf=False)) is False
    assert book.enabled(SimpleNamespace(url="print_page/", meta={})) is False
