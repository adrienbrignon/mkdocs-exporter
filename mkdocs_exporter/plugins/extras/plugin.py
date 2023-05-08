from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.plugins.extras.config import Config


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def on_post_page(self, html: str, page: Page, **kwargs) -> None | str:
    """Invoked after a page has been built."""

    preprocessor = Preprocessor()

    preprocessor.preprocess(html)

    for button in self.config.buttons:
      preprocessor.button(**{k: v(page) if callable(v) else v for k, v in button.items()})

    return preprocessor.done()
