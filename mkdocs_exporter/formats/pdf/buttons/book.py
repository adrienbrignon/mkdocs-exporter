from typing import Any

from mkdocs.utils import get_relative_url

from mkdocs_exporter.page import Page


def _book(page: Page) -> dict[str, Any] | None:
    """The first book including the page, if any."""

    books = getattr(page, "formats", {}).get("pdf", {}).get("books", [])

    return books[0] if books else None


def enabled(page: Page, **kwargs: Any) -> bool:
    """Is the button enabled (is the page part of a book)?"""

    return _book(page) is not None


def href(page: Page, **kwargs: Any) -> str:
    """The URL of the first book including the page, relative to the page."""

    book = _book(page)

    return get_relative_url(book["url"], page.url) if book else ""


def download(page: Page, **kwargs: Any) -> str:
    """The name of the downloaded file (the book's title)."""

    book = _book(page)

    return f"{book['title']}.pdf" if book else ""


def attributes(page: Page, **kwargs: Any) -> dict[str, str]:
    """The button's attributes."""

    return {
        "href": href(page, **kwargs),
        "download": download(page, **kwargs),
    }
