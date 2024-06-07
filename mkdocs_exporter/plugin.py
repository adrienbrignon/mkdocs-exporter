import logging

from typing import Type

from mkdocs.plugins import event_priority
from mkdocs.structure.files import File, Files
from mkdocs.plugins import BasePlugin, CombinedEvent

from mkdocs_exporter.page import Page
from mkdocs_exporter.config import Config
from mkdocs_exporter.logging import logger
from mkdocs_exporter.helpers import resolve
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.themes.factory import Factory as ThemeFactory
from mkdocs_exporter.formats.pdf.plugin import Plugin as PDFFormatPlugin


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def __init__(self) -> None:
    """The constructor."""

    self.stylesheets: list[File] = []
    self.on_post_page = CombinedEvent(self._on_post_page_1, self._on_post_page_2)


  @event_priority(100)
  def on_config(self, config: dict, *args, **kwargs) -> None:
    """Invoked when the configuration has been loaded."""

    self.theme = ThemeFactory.create(self.config.theme or config['theme'])

    if 'level' in self.config.logging:
      logger.setLevel(logging.getLevelName(self.config.logging.level.upper()))

    def register(key, plugin: Type[Plugin], config_data: dict) -> Plugin:
      """Registers a MkDocs plugin dynamically."""

      key = 'exporter-' + key

      config.plugins[key] = plugin()
      config.plugins[key].config = config_data

      config.plugins[key].on_config(config, *args, **kwargs)

    if 'pdf' in self.config.formats:
      register('pdf', PDFFormatPlugin, self.config['formats']['pdf'])


  def on_pre_build(self, **kwargs) -> None:
    """Invoked before the build process starts."""

    self.stylesheets.clear()


  @event_priority(100)
  def on_pre_page(self, page: Page, **kwargs) -> None:
    """Invoked before a page has been built."""

    page.html = None
    page.formats = {}
    page.theme = self.theme


  @event_priority(100)
  def _on_post_page_1(self, html: str, page: Page, **kwargs) -> str:
    """Invoked after a page has been built (and before all other plugins)."""

    page.html = html


  @event_priority(-100)
  def _on_post_page_2(self, html: str, page: Page, **kwargs) -> str:
    """Invoked after a page has been built (and after all other plugins)."""

    preprocessor = Preprocessor(theme=page.theme)

    preprocessor.preprocess(html)

    for button in [*self.config.buttons, *page.meta.get('buttons', [])]:
      if resolve(button.get('enabled', True), page=page):
        preprocessor.button(**resolve(button, page=page))

    preprocessor.remove('*[data-decompose="true"]')
    preprocessor.teleport()

    return preprocessor.done()


  def on_files(self, files: Files, **kwargs) -> Files:
    """Invoked when files are ready to be manipulated."""

    self.stylesheets.extend(files.css_files())

    return files


  @event_priority(100)
  def on_post_build(self, **kwargs) -> None:
    """Invoked when the build process is done."""

    for stylesheet in self.stylesheets:
      content = None

      with open(stylesheet.abs_dest_path, 'r', encoding='utf-8') as reader:
        content = self.theme.stylesheet(stylesheet, reader.read())
      with open(stylesheet.abs_dest_path, 'w+', encoding='utf-8') as writer:
        writer.write(content)
