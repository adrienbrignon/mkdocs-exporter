from typing import Optional
from mkdocs_exporter.theme import Theme
from mkdocs.structure.pages import Page as BasePage


class Page(BasePage):
  """A page."""


  def __init__(self, *args, **kwargs):
    """The constructor."""

    self.html: Optional[str] = None
    """The page's HTML content."""

    self.formats: dict[str, str]
    """The documents that have been generated for this page (format as key, path to the file as value)."""

    self.theme: Theme = None
    """The theme of the page."""

    super().__init__(*args, **kwargs)
