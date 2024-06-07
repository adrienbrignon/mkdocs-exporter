from __future__ import annotations

import os

from pypdf import PdfWriter

from mkdocs_exporter.formats.pdf.renderer import Renderer
from mkdocs_exporter.formats.pdf.preprocessor import Preprocessor


class Aggregator:
  """Aggregates PDF documents together."""


  def __init__(self, renderer: Renderer):
    """The constructor."""

    self.total_pages = 0
    self.renderer = renderer


  def open(self, path: str) -> Aggregator:
    """Opens the aggregator."""

    self.path = path
    self.writer = PdfWriter()


  def increment_total_pages(self, total_pages: int) -> Aggregator:
    """Increments the total pages count."""

    self.total_pages = self.total_pages + total_pages


  def preprocess(self, html: str, page_number: int = 1) -> str:
    """Preprocesses the page."""

    preprocessor = Preprocessor()

    preprocessor.preprocess(html)
    preprocessor.metadata({'page': page_number, 'pages': self.total_pages})

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
