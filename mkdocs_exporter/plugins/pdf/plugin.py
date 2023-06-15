import os
import types
import asyncio
import nest_asyncio

from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs.plugins import event_priority
from mkdocs_exporter.logging import logger
from mkdocs.livereload import LiveReloadServer
from typing import Optional, Coroutine, Sequence
from mkdocs_exporter.plugins.pdf.config import Config
from mkdocs_exporter.plugins.pdf.renderer import Renderer


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def __init__(self):
    """The constructor."""

    self.watch: list[str] = []
    self.renderer: Optional[Renderer] = None
    self.tasks: list[types.CoroutineType] = []
    self.loop: asyncio.AbstractEventLoopPolicy = asyncio.new_event_loop()


  def on_startup(self, **kwargs) -> None:
    """Invoked when the plugin is starting..."""

    nest_asyncio.apply(self.loop)
    asyncio.set_event_loop(self.loop)


  def on_config(self, config: dict) -> None:
    """Invoked when the configuration has been validated."""

    self.watch = []


  def on_serve(self, server: LiveReloadServer, **kwargs) -> LiveReloadServer:
    """Invoked when the website is being served."""

    if not self._enabled():
      return
    for path in [*self.config.stylesheets, *self.config.scripts]:
      server.watch(path)
    for path in set(os.path.normpath(path) for path in self.watch):
      server.watch(path)

    return server


  def on_page_markdown(self, markdown: str, page: Page, config: Config, **kwargs) -> str:
    """Invoked when the page's markdown has been loaded."""

    if not self._enabled(page) or 'covers' in page.meta.get('hide', []):
      return

    content = markdown
    covers = {**self.config.covers, **{k: os.path.join(os.path.dirname(config['config_file_path']), v) for k, v in page.meta.get('covers', {}).items()}}

    if covers.get('front'):
      with open(covers['front'], 'r', encoding='utf-8') as file:
        content = self.renderer.cover(file.read()) + content
    if covers.get('back'):
      with open(covers['back'], 'r', encoding='utf-8') as file:
        content = content + self.renderer.cover(file.read())

    for path in [path for path in covers.values() if path is not None]:
      self.watch.append(path)

    return content


  def on_pre_build(self, **kwargs) -> None:
    """Invoked before the build process starts."""

    self.tasks.clear()

    if not self._enabled():
      return

    self.renderer = Renderer(browser_options=self.config.browser)

    for stylesheet in self.config.stylesheets:
      self.renderer.add_stylesheet(stylesheet)
    for script in self.config.scripts:
      self.renderer.add_script(script)


  def on_pre_page(self, page: Page, config: dict, **kwargs):
    """Invoked before building the page."""

    if not self._enabled():
      return
    if not hasattr(page, 'html'):
      raise Exception('Missing `mkdocs/exporter` plugin or your plugins are not ordered properly!')

    directory = os.path.dirname(page.file.abs_dest_path)
    filename = os.path.splitext(os.path.basename(page.file.abs_dest_path))[0] + '.pdf'
    fullpath = os.path.join(directory, filename)

    page.formats['pdf'] = os.path.relpath(fullpath, config['site_dir'])


  @event_priority(-75)
  def on_post_page(self, html: str, page: Page, config: dict) -> Optional[str]:
    """Invoked after a page has been built."""

    if not self._enabled(page) and 'pdf' in page.formats:
      del page.formats['pdf']
    if 'pdf' not in page.formats:
      return html

    page.html = html

    async def render(page: Page) -> None:
      logger.info("[pdf] Rendering '%s'...", page.file.src_path)

      html = self.renderer.preprocess(page)
      pdf = await self.renderer.render(html)

      page.html = None

      with open(os.path.join(config['site_dir'], page.formats['pdf']), 'wb+') as file:
        file.write(pdf)
        logger.info("[pdf] File written to '%s'!", file.name)

    self.tasks.append(render(page))

    return page.html


  def on_post_build(self, **kwargs) -> None:
    """Invoked after the build process."""

    if not self._enabled():
      return

    def concurrently(coroutines: Sequence[Coroutine], concurrency: int) -> Sequence[Coroutine]:
      semaphore = asyncio.Semaphore(concurrency)

      async def limit(coroutine: Coroutine) -> Coroutine:
        async with semaphore:
          return await asyncio.create_task(coroutine)

      return [limit(coroutine) for coroutine in coroutines]

    self.loop.run_until_complete(asyncio.gather(*concurrently(self.tasks, max(1, self.config.concurrency or 1))))
    self.loop.run_until_complete(self.renderer.dispose())
    self.tasks.clear()

    self.renderer = None


  def _enabled(self, page: Page = None) -> bool:
    """Is the plugin enabled for this page?"""

    if not self.config.enabled:
      return False
    if page and not page.meta.get('pdf', not self.config.explicit):
      return False

    return True
