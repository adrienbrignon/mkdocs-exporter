from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.plugins import event_priority
from mkdocs.structure.files import File, Files
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.themes.factory import Factory as ThemeFactory


class Plugin(BasePlugin):
  """The plugin."""


  def __init__(self) -> None:
    """The constructor."""

    self.files: list[File] = []


  def on_config(self, config: dict) -> None:
    """Invoked when the configuration has been loaded."""

    self.theme = ThemeFactory.create(config['theme'])


  def on_pre_build(self, **kwargs) -> None:
    """Invoked before the build process starts."""

    self.files = []


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
    preprocessor.remove('*[data-decompose=true]')
    preprocessor.teleport()

    return preprocessor.done()


  def on_files(self, files: Files, **kwargs) -> Files:
    """Invoked when files are ready to be manipulated."""

    self.files.extend(files.css_files())

    return files


  @event_priority(100)
  def on_post_build(self, **kwargs) -> None:
    """Invoked when the build process is done."""

    for file in self.files:
      css = None

      with open(file.abs_dest_path, 'r') as reader:
        css = self.theme.stylesheet(reader.read())
      with open(file.abs_dest_path, 'w+') as writer:
        writer.write(css)
