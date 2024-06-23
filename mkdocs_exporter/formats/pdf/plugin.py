import os
import types
import asyncio

from typing import Optional

from mkdocs.plugins import event_priority
from mkdocs.livereload import LiveReloadServer
from mkdocs.plugins import BasePlugin, CombinedEvent

from mkdocs_exporter.page import Page
from mkdocs_exporter.helpers import concurrently
from mkdocs_exporter.logging import logger
from mkdocs_exporter.formats.pdf.config import Config
from mkdocs_exporter.formats.pdf.renderer import Renderer
from mkdocs_exporter.formats.pdf.aggregator import Aggregator


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def __init__(self):
    """The constructor."""

    self.watch: list[str] = []
    self.renderer: Optional[Renderer] = None
    self.tasks: list[types.CoroutineType] = []
    self.aggregator: Optional[Aggregator] = None
    self.loop: Optional[asyncio.AbstractEventLoopPolicy] = None
    self.on_post_build = CombinedEvent(self._on_post_build_1, self._on_post_build_2, self._on_post_build_3)


  def on_config(self, config: dict) -> None:
    """Invoked when the configuration has been validated."""

    self.watch = []

    if self.config.get('url') is None:
      self.config['url'] = config['site_url']


  def on_serve(self, server: LiveReloadServer, **kwargs) -> LiveReloadServer:
    """Invoked when the website is being served."""

    if not self._enabled():
      return
    for path in [*self.config.stylesheets, *self.config.scripts]:
      server.watch(path)
    for path in set(os.path.normpath(path) for path in self.watch):
      server.watch(path)

    return server


  @event_priority(100)
  def on_page_markdown(self, markdown: str, page: Page, config: Config, **kwargs) -> str:
    """Invoked when the page's markdown has been loaded."""

    if not self._enabled(page) or 'covers' in page.meta.get('hide', []):
      return

    content = markdown
    covers = {**self.config.covers, **{k: os.path.join(os.path.dirname(config['config_file_path']), v) for k, v in page.meta.get('covers', {}).items()}}

    for path in [path for path in covers.values() if path is not None]:
      self.watch.append(path)

    if covers.get('front'):
      page.formats['pdf']['covers'].append('front')

      with open(covers['front'], 'r', encoding='utf-8') as file:
        content = self.renderer.cover(file.read(), 'front') + content

    if covers.get('back'):
      page.formats['pdf']['covers'].append('back')

      with open(covers['back'], 'r', encoding='utf-8') as file:
        content = content + self.renderer.cover(file.read(), 'back')

    return content


  def on_pre_build(self, **kwargs) -> None:
    """Invoked before the build process starts."""

    if not self._enabled():
      return

    self.loop = asyncio.new_event_loop()
    self.renderer = Renderer(options=self.config)

    asyncio.set_event_loop(self.loop)

    if self.config.aggregator.get('enabled'):
      self.aggregator = Aggregator(renderer=self.renderer, config=self.config.get('aggregator'))
    for stylesheet in self.config.stylesheets:
      self.renderer.add_stylesheet(stylesheet)
    for script in self.config.scripts:
      self.renderer.add_script(script)


  @event_priority(90)
  def on_pre_page(self, page: Page, config: dict, **kwargs):
    """Invoked before building the page."""

    if not self._enabled():
      return

    directory = os.path.dirname(page.file.abs_dest_path)
    filename = os.path.splitext(os.path.basename(page.file.abs_dest_path))[0] + '.pdf'
    fullpath = os.path.join(directory, filename)

    page.formats['pdf'] = {
      'pages': 0,
      'covers': [],
      'path': fullpath,
      'skipped_pages': 0,
      'url': os.path.relpath(fullpath, config['site_dir'])
    }


  @event_priority(90)
  def on_post_page(self, html: str, page: Page, **kwargs) -> Optional[str]:
    """Invoked after a page has been built."""

    if not self._enabled(page) and 'pdf' in page.formats:
      del page.formats['pdf']

    if 'pdf' in page.formats:
      async def render(page: Page) -> None:
        logger.info("[mkdocs-exporter.pdf] Rendering '%s'...", page.file.src_path)

        html = self.renderer.preprocess(page)
        pdf, pages = await self.renderer.render(html)

        page.formats['pdf']['pages'] = pages

        with open(page.formats['pdf']['path'], 'wb+') as file:
          file.write(pdf)

      self.tasks.append(render(page))

    return page.html


  @event_priority(-90)
  def _on_post_build_1(self, **kwargs) -> None:
    """Invoked after the build process."""

    if not self._enabled():
      return
    while self.tasks:
      self.loop.run_until_complete(asyncio.gather(*concurrently(self.tasks, max(1, self.config.concurrency or 1))))


  @event_priority(-95)
  def _on_post_build_2(self, config: dict, **kwargs) -> None:
    """Invoked after the build process."""

    if not self._enabled() or not self.aggregator:
      return

    output = self.config['aggregator']['output']
    self.pages = [page for page in self.pages if 'pdf' in page.formats]

    self.aggregator.set_pages(self.pages)

    logger.info("[mkdocs-exporter.pdf] Aggregating pages to '%s'...", output)

    async def render(page: Page) -> None:
      html = self.aggregator.preprocess(page)
      pdf, _ = await self.renderer.render(html)

      with open(page.formats['pdf']['path'] + '.aggregate', 'wb+') as file:
        file.write(pdf)

    for page in self.pages:
      self.tasks.append(render(page))
    while self.tasks:
      self.loop.run_until_complete(asyncio.gather(*concurrently(self.tasks, max(1, self.config.concurrency or 1))))

    self.aggregator.open(os.path.join(config['site_dir'], output))

    for page in self.pages:
      self.aggregator.append(page.formats['pdf']['path'] + '.aggregate')
      os.unlink(page.formats['pdf']['path'] + '.aggregate')

    self.aggregator.save()


  @event_priority(-100)
  def _on_post_build_3(self, **kwargs) -> None:
    """Invoked after the build process."""

    if not self._enabled():
      return

    self.loop.run_until_complete(self.renderer.dispose())

    self.loop = None
    self.pages = None
    self.renderer = None
    self.aggregator = None

    asyncio.set_event_loop(self.loop)


  @event_priority(-100)
  def on_nav(self, nav, **kwargs):
    """Invoked when the navigation is ready."""

    def flatten(items):
      pages = []

      for item in items:
        if item.is_page:
          pages.append(item)
        if item.is_section:
          pages = pages + flatten(item.children)

      return pages

    self.pages = flatten(nav)

    for index, page in enumerate(self.pages):
      page.index = index


  def _enabled(self, page: Page = None) -> bool:
    """Is the plugin enabled for this page?"""

    if not self.config.enabled:
      return False
    if page and not page.meta.get('pdf', not self.config.explicit):
      return False

    return True
