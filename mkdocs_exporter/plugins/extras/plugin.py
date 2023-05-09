from typing import Optional
from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.plugins import event_priority
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.plugins.extras.config import Config


class Plugin(BasePlugin[Config]):
  """The plugin."""


  @event_priority(-85)
  def on_post_page(self, html: str, page: Page, **kwargs) -> Optional[str]:
    """Invoked after a page has been built."""

    def resolve(value):
      if callable(value):
        return value(page)

      return value

    preprocessor = Preprocessor()

    preprocessor.preprocess(html)

    for button in self.config.buttons:
      if resolve(button['enabled']):
        preprocessor.button(**{k: resolve(v) for k, v in button.items()})

    return preprocessor.done()
