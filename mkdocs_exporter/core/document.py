"""The data the core works on."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Site:
    """A built website."""

    directory: Path
    """The directory holding the built website."""

    url: str | None = None
    """The canonical URL of the website (e.g. `https://example.org/docs/`)."""

    @property
    def prefix(self) -> str:
        """The path under which the website is served (e.g. `/docs/`)."""

        path = urlsplit(self.url or "").path or "/"

        return path if path.endswith("/") else path + "/"


@dataclass
class Document:
    """A page of the website to export as a PDF document."""

    id: str
    """A unique identifier (e.g. the page's source path)."""

    url: str
    """The URL of the page, relative to the website's root (e.g. `guide/intro/`)."""

    path: str
    """The location of the PDF document, relative to the website's root."""

    title: str = ""
    """The page's title."""

    html: str = ""
    """The page's HTML, as built."""

    meta: dict[str, Any] = field(default_factory=dict)
    """The page's metadata."""

    covers: dict[str, str] = field(default_factory=dict)
    """The HTML of the document's cover pages, by location (`front`, `back`)."""

    @property
    def directory(self) -> str:
        """The directory of the PDF document, relative to the website's root."""

        return posixpath.dirname(self.path)


@dataclass
class Layout:
    """The layout of a rendered document."""

    pages: int
    """The number of pages."""

    cover_pages: dict[str, int] = field(default_factory=dict)
    """The number of pages that only hold a cover, by cover location."""
