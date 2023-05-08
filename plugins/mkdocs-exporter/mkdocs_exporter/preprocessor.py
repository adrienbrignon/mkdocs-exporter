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


  def preprocess(self, html: str) -> Self:
    """Gives the preprocessor some HTML to work on."""

    self.html = BeautifulSoup(html, 'lxml') if isinstance(html, str) else None

    return self


  def button(self, title: str, href: str, icon: str, **kwargs) -> Self:
    """Adds a button at the top of the page."""

    button = self.html.new_tag('a', title=title, href=href, **kwargs, attrs={'class': 'md-content__button md-icon'})
    svg = BeautifulSoup(icon, 'lxml')

    button.append(svg)
    self.html.find('article', { 'class': 'md-content__inner' }).insert(0, button)

    return self


  def script(self, script: str = None, type: str = 'text/javascript', **kwargs):
    """Appends a script to the document's body."""

    element = self.html.new_tag('script', type=type, **kwargs)

    element.string = script

    self.html.body.append(element)


  def stylesheet(self, stylesheet: str, **kwargs) -> Self:
    """Appends a stylesheet to the document's head."""

    css = sass.compile(string=stylesheet, output_style='compressed')
    element = self.html.new_tag('style', type='text/css', rel='stylesheet', **kwargs)

    element.string = css

    self.html.head.append(element)


  def remove(self, selectors: list[str]) -> Self:
    """Removes some elements."""

    for selector in selectors:
      for element in self.html.select(selector):
        element.decompose()


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
