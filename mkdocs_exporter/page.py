from mkdocs.structure.pages import Page as BasePage

from mkdocs_exporter.theme import Theme


class Page(BasePage):
    """A page."""

    index: int
    """The page's index."""

    html: str | None = None
    """The page's HTML content."""

    formats: dict[str, dict]
    """The documents generated for this page (format as key, details as value)."""

    theme: Theme = None
    """The theme of the page."""
