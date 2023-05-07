import os
import types
import asyncio

from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs_exporter.logging import logger
from mkdocs_exporter.plugins.pdf.config import Config
from mkdocs_exporter.plugins.pdf.renderer import Renderer


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def __init__(self):
    """The constructor."""

    self.renderer: None | Renderer = None
    self.tasks: list[types.CoroutineType] = []
    self.loop: None | asyncio.AbstractEventLoop = None


  def on_pre_build(self, config: dict, **kwargs) -> None:
    """Invoked before the build process starts."""

    if not self.config.enabled:
      return
    if self.loop and self.loop.is_running():
      self.loop.close()

    self.tasks.clear()

    self.renderer = Renderer()

    for stylesheet in self.config.stylesheets:
      self.renderer.add_stylesheet(os.path.join(os.path.dirname(config['config_file_path']), stylesheet))


  def on_pre_page(self, page: Page, config: dict, **kwargs):
    """Invoked before building the page."""

    if not self.config.enabled:
      return

    directory = os.path.dirname(page.file.abs_dest_path)
    filename = os.path.splitext(os.path.basename(page.file.abs_src_path))[0] + '.pdf'
    fullpath = os.path.join(directory, filename)

    if page.meta.get('pdf', True):
      page.formats['pdf'] = os.path.relpath(fullpath, config['site_dir'])


  def on_post_page(self, html: str, page: Page, config: dict) -> None | str:
    """Invoked after a page has been built."""

    page.html = html

    if not self.config.enabled or 'pdf' not in page.formats:
      return html

    async def render(page: Page) -> None:
      logger.info('Rendering %s...', page.file.src_path)

      pdf = await self.renderer.render(page)
      fullpath = os.path.join(config['site_dir'], page.formats['pdf'])

      with open(fullpath, 'wb+') as file:
        file.write(pdf)

      logger.info('PDF file written to %s!', fullpath)

    self.tasks.append(render(page))

    return page.html


  def on_post_build(self, **kwargs):
    """Invoked after the build process."""

    if not self.config.enabled:
      return

    self.loop = asyncio.new_event_loop()

    def partition(list, n):
      for i in range(0, len(list), n):
        yield [self.loop.create_task(task) for task in list[i:i + n]]

    for tasks in partition(self.tasks, self.config.concurrency or 1):
      self.loop.run_until_complete(asyncio.gather(*tasks))

    self.loop.close()
    self.tasks.clear()


  def on_shutdown(self) -> None:
    """Invoked on shutdown..."""

    if self.loop and self.loop.is_running():
      self.loop.close()
