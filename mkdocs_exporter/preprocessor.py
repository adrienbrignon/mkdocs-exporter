from __future__ import annotations

import os
import sass
import json

from typing import Union
from sass import CompileError
from urllib.parse import urlparse
from bs4 import BeautifulSoup, Tag

from mkdocs_exporter.theme import Theme
from mkdocs_exporter.logging import logger


class Preprocessor():
  """The HTML preprocessor."""

  def __init__(self, html: str = None, **kwargs):
    """The constructor."""

    self.html = None
    self.theme = None

    if 'theme' in kwargs:
      self.set_theme(kwargs['theme'])

    self.preprocess(html)


  def set_theme(self, theme: Theme) -> Preprocessor:
    """Sets the current theme."""

    self.theme = theme

    return self


  def preprocess(self, html: str) -> Preprocessor:
    """Gives the preprocessor some HTML to work on."""

    self.html = BeautifulSoup(html, 'lxml') if isinstance(html, str) else None

    return self


  def teleport(self) -> Preprocessor:
    """Teleport elements to their destination."""

    for element in self.html.select('*[data-teleport]'):
      selector = element.attrs.get('data-teleport')
      destination = self.html.select_one(selector)
      tag = Tag(None, name=element.name, attrs=element.attrs)

      if destination is None:
        if element.string:
          tag.string = '...'

        logger.warn('Failed to teleport element `%s`: destination `%s` was not found', tag, selector)

        continue

      element.attrs.pop('data-teleport', None)
      destination.append(element)

    return self


  def button(self, title: str, icon: str, attributes: dict = {}, **kwargs) -> Preprocessor:
    """Adds a button at the top of the page."""

    if kwargs.get('enabled', True) and self.theme:
      self.theme.button(self, title, icon, attributes)

    return self


  def script(self, script: str = None, type: str = 'text/javascript', **kwargs) -> Preprocessor:
    """Appends a script to the document's body."""

    element = self.html.new_tag('script', type=type, **kwargs)

    element.string = script

    self.html.body.append(element)

    return self


  def stylesheet(self, stylesheet: str, **kwargs) -> Preprocessor:
    """Appends a stylesheet to the document's head."""

    css = None

    try:
      css = sass.compile(string=stylesheet, output_style='compressed')
    except CompileError as error:
      logger.error(error)

      return self

    element = self.html.new_tag('style', type='text/css', rel='stylesheet', **kwargs)

    element.string = css

    self.html.head.append(element)

    return self


  def remove(self, selectors: Union[str, list[str]]) -> Preprocessor:
    """Removes some elements."""

    if isinstance(selectors, str):
      selectors = [selectors]

    for selector in selectors:
      for element in self.html.select(selector):
        element.decompose()

    return self


  def set_attribute(self, selector: str, key: str, value: str) -> Preprocessor:
    """Set an attribute on elements matching the given selector."""

    for element in self.html.select(selector):
      element.attrs[key] = value

    return self


  def update_links(self, base: str, root: str = None) -> Preprocessor:
    """Updates links to their new base location."""

    for element in self.html.find_all('link', href=True):
      element['href'] = self._resolve_link(element['href'], base, root)
    for element in self.html.find_all(src=True):
      element['src'] = self._resolve_link(element['src'], base, root)

    return self


  def metadata(self, metadata: dict) -> Preprocessor:
    """Inserts metadata."""

    return self.script(f"window.__MKDOCS_EXPORTER__ = {json.dumps(metadata)};")


  def done(self) -> str:
    """End the preprocessing, returning the result."""

    result = str(self.html)

    self.html = None

    return result


  def _resolve_link(self, url: str, base: str, root: str = None) -> str:
    """Resolves a link to its new base location."""

    if bool(urlparse(url).netloc):
      return url
    if root is not None and os.path.isabs(url):
      return 'file://' + os.path.abspath(os.path.join(root, url.strip('/')))

    return 'file://' + os.path.abspath(os.path.join(base, url.strip('/')))
