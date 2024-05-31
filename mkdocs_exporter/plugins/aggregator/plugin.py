import os

from pypdf import PdfReader, PdfWriter

from mkdocs.plugins import BasePlugin
from mkdocs.plugins import event_priority

from mkdocs_exporter.logging import logger
from mkdocs_exporter.plugins.aggregator.config import Config


class Plugin(BasePlugin[Config]):
  """The plugin."""

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

    self.nav = nav
    self.pages = flatten(nav)


  def on_post_build(self, config, **kwargs):
    """Invoked once the build is done."""

    if not self.config.get('enabled'):
      return

    logger.info('[mkdocs-exporter.aggregator] Generating aggregated PDF document...')

    aggregate = PdfWriter()
    destination = os.path.join(config['site_dir'], 'aggregate.pdf')

    for n, page in enumerate(self.pages):
      if 'pdf' not in page.formats:
        continue

      pages = None
      pdf = os.path.join(config['site_dir'], page.formats['pdf']['path'])

      if 'covers' in page.formats['pdf']:
        pages = (0 if n == 0 else 1, len(PdfReader(pdf).pages) - (0 if n == (len(self.pages) - 1) else 1))

      aggregate.append(pdf, pages=pages)

    aggregate.add_metadata({'/Producer': 'MkDocs Exporter'})
    aggregate.write(destination)
    aggregate.close()

    logger.info("[mkdocs-exporter.aggregator] Aggregated PDF document written to '%s'!", destination)
