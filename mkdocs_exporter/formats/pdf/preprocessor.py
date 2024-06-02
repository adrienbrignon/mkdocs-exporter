from __future__ import annotations
from urllib.parse import urlparse, urljoin

from mkdocs_exporter.preprocessor import Preprocessor as BasePreprocessor


class Preprocessor(BasePreprocessor):
  """The HTML preprocessor for PDF documents."""


  def rewrite_links(self, base: str, root: str) -> None:
    """Rewrite links based on the documentation's URL."""

    for element in self.html.find_all('a', href=True):
      url = urlparse(element['href'])

      if bool(url.netloc):
        continue
      if not url.path:
        continue

      final = urlparse(root)
      path = urljoin(base, url.path)

      element['href'] = url._replace(netloc=final.netloc, scheme=final.scheme, path=path).geturl()
