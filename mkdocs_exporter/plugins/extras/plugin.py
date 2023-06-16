from typing import Optional
from collections import UserDict
from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.plugins import event_priority
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.plugins.extras.config import Config


class Plugin(BasePlugin[Config]):
  """The plugin."""


  @event_priority(-85)
  def on_post_page(self, html: str, page: Page, config: dict, **kwargs) -> Optional[str]:
    """Invoked after a page has been built."""

    if not self.config.enabled:
      return

    def resolve(object):
      if callable(object):
        return resolve(object(page, config=config))
      if isinstance(object, list):
        return [resolve(v) for v in object]
      if isinstance(object, (dict, UserDict)):
        return {k: resolve(v) for k, v in object.items()}

      return object

    preprocessor = Preprocessor(theme=page.theme)

    preprocessor.preprocess(html)

    for button in [*self.config.buttons, *page.meta.get('buttons', [])]:
      if resolve(button.get('enabled', True)):
        preprocessor.button(**resolve(button))

    return preprocessor.done()
