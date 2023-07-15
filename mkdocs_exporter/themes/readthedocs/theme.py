
from __future__ import annotations

import importlib_resources

from mkdocs_exporter.resources import css
from mkdocs_exporter.theme import Theme as BaseTheme
from mkdocs_exporter.preprocessor import Preprocessor


class Theme(BaseTheme):
  """The "readthedocs" theme."""

  name = 'readthedocs'
  """The name of the theme."""


  def preprocess(self, preprocessor: Preprocessor) -> None:
    """Preprocesses the DOM before rendering a document."""

    preprocessor.remove(['.rst-content > div[role="navigation"]', 'nav.wy-nav-side'])
    preprocessor.stylesheet(importlib_resources.files(css).joinpath('readthedocs.css').read_text(encoding='utf-8'))


  def button(self, preprocessor: Preprocessor, title: str, icon: str, attributes: dict = {}):
    """Inserts a custom themed button."""

    button = preprocessor.html.new_tag('a', title=title, attrs={'class': 'btn btn-neutral float-right', **attributes})
    button.string = title

    preprocessor.html.find('div', {'class': 'document'}).insert(0, button)


  def icon(self, name: str):
    """Gets a themed icon."""

    return None


  def stylesheet(self, css: str) -> str:
    """Transforms a stylesheet."""

    return css.replace(':nth-of-type(3n+1)', ':nth-of-type(3n)')
