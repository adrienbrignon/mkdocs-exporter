
from __future__ import annotations

from bs4 import BeautifulSoup

from mkdocs_exporter.theme import Theme as BaseTheme
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.themes.material.icons import get_icon


class Theme(BaseTheme):
  """The "material" theme."""

  name = 'material'
  """The name of the theme."""


  def preprocess(self, preprocessor: Preprocessor) -> None:
    """Preprocesses the DOM before rendering a document."""

    preprocessor.remove(['.md-sidebar.md-sidebar--primary', '.md-sidebar.md-sidebar--secondary', 'header.md-header', '.md-container > nav', 'nav.md-tags'])


  def button(self, preprocessor: Preprocessor, title: str, icon: str, attributes: dict = {}):
    """Inserts a custom themed button."""

    tags = preprocessor.html.find('nav', {'class': 'md-tags'})
    button = preprocessor.html.new_tag('a', title=title, attrs={'class': 'md-content__button md-icon', **attributes})
    icon = self.icon(icon) or self.icon('material-progress-question')

    button.append(BeautifulSoup(icon, 'lxml'))

    if tags:
      tags.insert_after(button)
    else:
      preprocessor.html.find('article', {'class': 'md-content__inner'}).insert(0, button)

    return self


  def icon(self, name: str):
    """Gets a themed icon."""

    return get_icon(name)
