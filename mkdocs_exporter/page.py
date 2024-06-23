from typing import Optional

from mkdocs_exporter.theme import Theme
from mkdocs.structure.pages import Page as BasePage


class Page(BasePage):
  """A page."""

  index: int
  """The page's index."""

  html: Optional[str] = None
  """The page's HTML content."""

  formats: dict[str, dict]
  """The documents that have been generated for this page (format as key, path to the file as value)."""

  theme: Theme = None
  """The theme of the page."""
