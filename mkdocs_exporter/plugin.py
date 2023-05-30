from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.plugins import event_priority
from mkdocs_exporter.config import Config
from mkdocs.structure.files import File, Files
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.themes.factory import Factory as ThemeFactory


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def __init__(self) -> None:
    """The constructor."""

    self.stylesheets: list[File] = []


  def on_config(self, config: dict) -> None:
    """Invoked when the configuration has been loaded."""

    self.theme = ThemeFactory.create(self.config.theme or config['theme'])


  def on_pre_build(self, **kwargs) -> None:
    """Invoked before the build process starts."""

    self.stylesheets.clear()


  def on_pre_page(self, page: Page, **kwargs) -> None:
    """Invoked after a page has been built."""

    page.html = None
    page.formats = {}
    page.theme = self.theme


  @event_priority(-100)
  def on_post_page(self, html: str, page: Page, **kwargs) -> str:
    """Invoked after a page has been built (and after all other plugins)."""

    preprocessor = Preprocessor(theme=page.theme)

    preprocessor.preprocess(html)
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
        content = self.theme.stylesheet(reader.read())
      with open(stylesheet.abs_dest_path, 'w+', encoding='utf-8') as writer:
        writer.write(content)
