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
    destination = os.path.join(config['site_dir'], self.config['output'])

    os.makedirs(os.path.dirname(destination), exist_ok=True)

    for n, page in enumerate(self.pages):
      if 'pdf' not in page.formats:
        continue

      pages = None
      pdf = os.path.join(config['site_dir'], page.formats['pdf']['path'])
      total = len(PdfReader(pdf).pages)

      if 'covers' in page.formats['pdf']:
        covers = page.formats['pdf']['covers']

        if self.config['covers'] == 'none':
          pages = (1 if covers['front'] else 0, (total - 1) if covers['back'] else total)
        if self.config['covers'] == 'limits':
          pages = (1 if n != 0 and covers['front'] else 0, (total - 1) if n != (len(self.pages) - 1) and covers['back'] else total)

      aggregate.append(pdf, pages=pages)

    if len(aggregate.pages) > 0:
      aggregate.add_metadata({'/Producer': 'MkDocs Exporter', **self.config['metadata']})
      aggregate.write(destination)
      logger.info("[mkdocs-exporter.aggregator] Aggregated PDF document written to '%s'!", destination)

    aggregate.close()
