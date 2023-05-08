import os
import types
import asyncio

from weasyprint import urls
from typing import Optional
from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.structure.pages import Page
from mkdocs.plugins import event_priority
from mkdocs_exporter.logging import logger
from mkdocs.livereload import LiveReloadServer
from mkdocs_exporter.plugins.pdf.config import Config
from mkdocs_exporter.plugins.pdf.renderer import Renderer


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def __init__(self):
    """The constructor."""

    self.renderer: Optional[Renderer] = None
    self.tasks: list[types.CoroutineType] = []
    self.loop: Optional[asyncio.AbstractEventLoop] = None


  def on_config(self, config: dict) -> None:
    """Invoked when the configuration has been validated."""

    def resolve(path: str) -> str:
      if path is None:
        return None
      if urls.url_is_absolute(path):
        return path

      return os.path.join(os.path.dirname(config['config_file_path']), path)

    self.config.covers.front = resolve(self.config.covers.front)
    self.config.covers.back = resolve(self.config.covers.back)
    self.config.scripts = [resolve(path) for path in self.config.scripts]
    self.config.stylesheets = [resolve(path) for path in self.config.stylesheets]


  def on_serve(self, server: LiveReloadServer, **kwargs) -> LiveReloadServer:
    """Invoked when the website is being served."""

    for path in [*self.config.stylesheets, *self.config.scripts]:
      server.watch(path)
    for cover in self.config.covers:
      server.watch(self.config.covers[cover])

    return server


  def on_page_markdown(self, markdown: str, **kwargs) -> str:
    """Invoked when the page's markdown has been loaded."""

    content = markdown

    if self.config.covers.front:
      with open(self.config.covers.front, 'r') as file:
        content = self.renderer.cover(file.read()) + content
    if self.config.covers.back:
      with open(self.config.covers.back, 'r') as file:
        content = content + self.renderer.cover(file.read())

    return content


  def on_pre_build(self, **kwargs) -> None:
    """Invoked before the build process starts."""

    if not self.config.enabled:
      return
    if self.loop and self.loop.is_running():
      self.loop.close()

    self.tasks.clear()

    self.renderer = Renderer()

    for stylesheet in self.config.stylesheets:
      self.renderer.add_stylesheet(stylesheet)
    for script in self.config.scripts:
      self.renderer.add_script(script)


  def on_pre_page(self, page: Page, config: dict, **kwargs):
    """Invoked before building the page."""

    if not self.config.enabled:
      return

    directory = os.path.dirname(page.file.abs_dest_path)
    filename = os.path.splitext(os.path.basename(page.file.abs_src_path))[0] + '.pdf'
    fullpath = os.path.join(directory, filename)

    if page.meta.get('pdf', True):
      page.formats['pdf'] = os.path.relpath(fullpath, config['site_dir'])


  @event_priority(-75)
  def on_post_page(self, html: str, page: Page, config: dict) -> Optional[str]:
    """Invoked after a page has been built."""

    page.html = html

    if not self.config.enabled or 'pdf' not in page.formats:
      return html

    async def render(page: Page) -> None:
      logger.info('[PDF] Rendering %s...', page.file.src_path)

      pdf = await self.renderer.render(page, polyfills=self.config['polyfills'])
      fullpath = os.path.join(config['site_dir'], page.formats['pdf'])

      with open(fullpath, 'wb+') as file:
        file.write(pdf)

      logger.info('[PDF] File written to %s!', fullpath)

    self.tasks.append(render(page))

    return page.html


  def on_post_build(self, **kwargs) -> None:
    """Invoked after the build process."""

    if not self.config.enabled:
      return

    self.loop = asyncio.new_event_loop()

    def partition(list, n):
      for i in range(0, len(list), n):
        yield [self.loop.create_task(task) for task in list[i:i + n]]

    for tasks in partition(self.tasks, self.config.concurrency or 1):
      self.loop.run_until_complete(asyncio.gather(*tasks))

    self.tasks.clear()
    self.loop.run_until_complete(self.renderer.dispose())
    self.loop.close()

    self.renderer = None


  def on_shutdown(self) -> None:
    """Invoked on shutdown..."""

    if self.loop and self.loop.is_running():
      self.loop.stop()
