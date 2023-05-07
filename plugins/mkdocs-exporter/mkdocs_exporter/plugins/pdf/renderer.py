import os

from mkdocs_exporter.page import Page
from mkdocs_exporter.browser import Browser
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.renderer import Renderer as BaseRenderer


class Renderer(BaseRenderer):
  """The renderer."""

  def __init__(self, browser: Browser = None):
    """The constructor."""

    self.stylesheets: list[str] = []
    self.browser = browser or Browser()


  def add_stylesheet(self, path: str):
    """Adds a stylesheet to the renderer."""

    with open(path, 'r') as file:
      self.stylesheets.append(file.read())


  async def render(self, page: Page) -> bytes:
    """Renders a page as a PDF document."""

    if not self.browser.launched:
      await self.browser.launch()

    preprocessor = Preprocessor()
    base = os.path.dirname(page.file.abs_dest_path)

    os.makedirs(base, exist_ok=True)

    preprocessor.preprocess(page.html)

    for stylesheet in self.stylesheets:
      preprocessor.stylesheet(stylesheet)

    preprocessor.remove_scripts()
    preprocessor.update_links(base)

    return await self.browser.print(preprocessor.done())
