from __future__ import annotations

from bs4 import BeautifulSoup
from mkdocs_exporter.plugins.extras.icon import get_svg_icon
from mkdocs_exporter.preprocessor import Preprocessor as BasePreprocessor


class Preprocessor(BasePreprocessor):
  """An extended preprocessor."""


  def button(self, title: str, href: str, icon: str, **kwargs) -> Preprocessor:
    """Adds a button at the top of the page."""

    tags = self.html.find('nav', {'class': 'md-tags'})
    button = self.html.new_tag('a', title=title, href=href, **kwargs, attrs={'class': 'md-content__button md-icon'})
    svg = BeautifulSoup(get_svg_icon(icon) or get_svg_icon('material-progress-question'), 'lxml')

    button.append(svg)

    if tags:
      tags.insert_after(button)
    else:
      self.html.find('article', {'class': 'md-content__inner'}).insert(0, button)

    return self
