from typing import Optional
from collections import UserDict
from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.plugins import event_priority
from mkdocs_exporter.logging import logger
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.plugins.extras.config import Config


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def on_config(self, *args, **kwargs) -> None:
    """Invoked when the configuration has been loaded."""

    pass


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


class DeprecatedPlugin(Plugin):
  """Deprecated plugin, will be removed in the next major release."""


  def on_config(self, *args, **kwargs) -> None:
    """Invoked when the configuration has been loaded."""

    logger.warning("The plugin name 'mkdocs/exporter/extras' will stop working soon, please replace it with 'exporter-extras'")

    super().on_config(*args, **kwargs)
