from __future__ import annotations

import os

from pypdf import PdfReader, PdfWriter


class Aggregator:
  """Aggregates PDF documents together."""


  def open(self, path: str) -> Aggregator:
    """Opens the aggregator."""

    self.path = path
    self.writer = PdfWriter()


  def covers(self, mode: str) -> Aggregator:
    """Defines the way of handling cover pages."""

    self._covers = mode


  def aggregate(self, pages: list) -> Aggregator:
    """Aggregates pages together."""

    for n, page in enumerate(pages):
      if 'pdf' not in page.formats:
        continue

      bounds = None
      pdf = page.formats['pdf']['path']
      total = len(PdfReader(pdf).pages)

      if 'covers' in page.formats['pdf']:
        covers = page.formats['pdf']['covers']

        if self._covers == 'none':
          bounds = (1 if covers['front'] else 0, (total - 1) if covers['back'] else total)
        if self._covers == 'limits':
          bounds = (1 if n != 0 and covers['front'] else 0, (total - 1) if n != (len(pages) - 1) and covers['back'] else total)

      self.writer.append(pdf, pages=bounds)


  def save(self, metadata={}) -> Aggregator:
    """Saves the aggregated document."""

    os.makedirs(os.path.dirname(self.path), exist_ok=True)

    self.writer.add_metadata({'/Producer': 'MkDocs Exporter', **metadata})
    self.writer.write(self.path)
    self.writer.close()

    self.writer = None

    return self
