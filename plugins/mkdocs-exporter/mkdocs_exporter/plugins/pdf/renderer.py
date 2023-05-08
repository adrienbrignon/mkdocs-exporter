import os

from typing import Self
from mkdocs_exporter.page import Page
from mkdocs_exporter.browser import Browser
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.renderer import Renderer as BaseRenderer


class Renderer(BaseRenderer):
  """The renderer."""

  def __init__(self, browser: Browser = None):
    """The constructor."""

    self.back_cover = None
    self.front_cover = None
    self.scripts: list[str] = []
    self.stylesheets: list[str] = []
    self.browser = browser or Browser()


  def add_stylesheet(self, path: str) -> Self:
    """Adds a stylesheet to the renderer."""

    self.stylesheets.append(path)

    return self


  def add_script(self, path: str) -> Self:
    """Adds a script to the renderer."""

    self.scripts.append(path)

    return self


  def set_front_cover(self, template: str) -> Self:
    """Sets the front cover."""

    self.front_cover = template


  async def render(self, page: Page) -> bytes:
    """Renders a page as a PDF document."""

    if not self.browser.launched:
      await self.browser.launch()

    preprocessor = Preprocessor()
    base = os.path.dirname(page.file.abs_dest_path)

    os.makedirs(base, exist_ok=True)

    preprocessor.preprocess(page.html)
    preprocessor.remove(['.md-sidebar.md-sidebar--primary', '.md-sidebar.md-sidebar--secondary', 'header.md-header', '.md-container > nav'])
    preprocessor.remove_scripts()
    preprocessor.update_links(base)

    for stylesheet in self.stylesheets:
      with open(stylesheet, 'r') as file:
        preprocessor.stylesheet(file.read())
    for script in self.scripts:
      with open(script, 'r') as file:
        preprocessor.script(file.read())

    html = preprocessor.done()

    return await self.browser.print(html)


  async def dispose(self):
    """Dispose of the renderer."""

    if self.browser:
      await self.browser.close()
