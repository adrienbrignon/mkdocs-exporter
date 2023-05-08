from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.plugins import event_priority
from mkdocs_exporter.preprocessor import Preprocessor


class Plugin(BasePlugin):
  """The plugin."""


  def on_pre_page(self, page: Page, **kwargs) -> None:
    """Invoked after a page has been built."""

    page.html = None
    page.formats = {}


  @event_priority(-100)
  def on_post_page(self, html: str, **kwargs) -> str | None:
    """Invoked after a page has been built (and after all other plugins)."""

    preprocessor = Preprocessor()

    preprocessor.preprocess(html)
    preprocessor.remove('*[data-decompose=true]')
    preprocessor.teleport()

    return preprocessor.done()
