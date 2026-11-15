from typing import Any

from mkdocs.utils import get_relative_url

from mkdocs_exporter.page import Page


def enabled(page: Page, **kwargs: Any) -> bool:
    """Is the button enabled (does the page have a PDF document)?"""

    return "pdf" in getattr(page, "formats", {})


def href(page: Page, **kwargs: Any) -> str:
    """The URL of the page's PDF document, relative to the page."""

    return get_relative_url(page.formats["pdf"]["url"], page.url)


def download(page: Page, **kwargs: Any) -> str:
    """The name of the downloaded file."""

    return page.title + ".pdf"


def attributes(page: Page, **kwargs: Any) -> dict[str, str]:
    """The button's attributes."""

    return {
        "href": href(page, **kwargs),
        "download": download(page, **kwargs),
    }


def icon(page: Page, **kwargs: Any) -> str:
    """The button's icon."""

    return str(page.meta.get("pdf-icon", "material-file-download-outline"))
