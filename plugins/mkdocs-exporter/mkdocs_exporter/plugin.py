from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page


class Plugin(BasePlugin):
  """The plugin."""


  def on_pre_page(self, page: Page, **kwargs) -> None:
    """Invoked after a page has been built."""

    page.html = None
    page.formats = {}
