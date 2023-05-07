import os
import sass

from weasyprint import urls
from bs4 import BeautifulSoup
from typing import Any, Callable, Self


class Preprocessor():
  """The HTML preprocessor."""

  def __init__(self, html: str = None):
    """The constructor."""

    self.preprocess(html)


  def button(self, title: str, href: str, download: bool | str, icon: str) -> Self:
    """Adds a button at the top of the page."""

    button = self.html.new_tag('a', title=title, href=href, download=download, attrs={'class': 'md-content__button md-icon'})
    svg = BeautifulSoup(icon, 'lxml')

    button.append(svg)
    self.html.find('article', { 'class': 'md-content__inner' }).insert(0, button)

    return self


  def stylesheet(self, stylesheet: str) -> Self:
    """Appends a stylesheet to the document's head."""

    element = self.html.new_tag('style', type='text/css', rel='stylesheet')

    element.string = sass.compile(string=stylesheet)

    self.html.head.append(element)


  def preprocess(self, html: str) -> Self:
    """Gives the preprocessor some HTML to work on."""

    self.html = BeautifulSoup(html, 'lxml') if isinstance(html, str) else None

    return self


  def remove_scripts(self, predicate: Callable[[Any], bool] = lambda _: True) -> Self:
    """Remove all script tags."""

    for element in self.html.find_all('script'):
      if predicate(element):
        element.decompose()

    return self


  def update_links(self, base: str) -> Self:
    """Updates links to their new base location."""

    for element in self.html.find_all('link', href=True):
      element['href'] = self._resolve_link(element['href'], base)
    for element in self.html.find_all(src=True):
      element['src'] = self._resolve_link(element['src'], base)

    return self


  def done(self) -> str:
    """End the preprocessing, returning the result."""

    result = str(self.html)

    self.html = None

    return result


  def _resolve_link(self, url: str, base: str):
    """Resolves a link to its new base location."""

    if urls.url_is_absolute(url):
      return url

    return 'file://' + os.path.abspath(os.path.join(base, url.strip('/')))
