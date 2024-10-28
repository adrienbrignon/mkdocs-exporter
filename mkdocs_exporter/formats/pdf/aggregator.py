from __future__ import annotations

import os

from pypdf import PdfWriter

from mkdocs_exporter.page import Page
from mkdocs_exporter.formats.pdf.renderer import Renderer
from mkdocs_exporter.formats.pdf.preprocessor import Preprocessor


class Aggregator:
  """Aggregates PDF documents together."""


  def __init__(self, renderer: Renderer, config: dict = {}) -> None:
    """The constructor."""

    self.pages = []
    self.config = config
    self.renderer = renderer


  def open(self, path: str) -> Aggregator:
    """Opens the aggregator."""

    self.path = path
    self.writer = PdfWriter()

    return self


  def set_pages(self, pages: list[Page]) -> Aggregator:
    """Sets the pages."""

    self.pages = pages
    covers = self.config.get('covers', [])

    for index, page in enumerate(self.pages):
      if covers == 'none':
        self._skip(page, ['front', 'back'])
      elif covers == 'front':
        self._skip(page, ['back'])
      elif covers == 'back':
        self._skip(page, ['front'])
      elif covers == 'limits':
        if len(self.pages) == 1:
          pass
        elif index == 0:
          self._skip(page, ['back'])
        elif index == (len(self.pages) - 1):
          self._skip(page, ['front'])
        else:
          self._skip(page, ['front', 'back'])
      elif covers == 'book':
        if len(self.pages) == 1:
          pass
        elif index == 0:
          self._skip(page, ['back'])
        elif index < (len(self.pages) - 1):
          self._skip(page, ['back'])

    return self


  def preprocess(self, page: Page) -> str:
    """Preprocesses the page."""

    preprocessor = Preprocessor()

    preprocessor.preprocess(self.renderer.preprocess(page, disable=['teleport']))

    if 'front' not in page.formats['pdf']['covers']:
      preprocessor.remove('div.mkdocs-exporter-front-cover')
    if 'back' not in page.formats['pdf']['covers']:
      preprocessor.remove('div.mkdocs-exporter-back-cover')

    preprocessor.teleport()
    preprocessor.metadata({
      'page': sum(page.formats['pdf']['pages'] - page.formats['pdf']['skipped_pages'] for page in self.pages[:page.index]) + 1,
      'pages': sum(page.formats['pdf']['pages'] - page.formats['pdf']['skipped_pages'] for page in self.pages),
    })

    return preprocessor.done()


  def append(self, document: str) -> Aggregator:
    """Appends a document to this one."""

    self.writer.append(document)

    return self


  def save(self, metadata={}) -> Aggregator:
    """Saves the aggregated document."""

    os.makedirs(os.path.dirname(self.path), exist_ok=True)

    self.writer.add_metadata({'/Producer': 'MkDocs Exporter', **metadata})
    self.writer.write(self.path)
    self.writer.close()

    self.writer = None

    return self


  def _skip(self, page: Page, covers: list[str]) -> Aggregator:
    """Skip cover pages."""

    for cover in covers:
      if cover in page.formats['pdf']['covers']:
        page.formats['pdf']['covers'].remove(cover)

        page.formats['pdf']['skipped_pages'] = page.formats['pdf']['skipped_pages'] + 1

    return self
