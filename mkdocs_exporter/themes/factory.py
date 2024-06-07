from mkdocs_exporter.theme import Theme
from mkdocs.theme import Theme as BaseTheme

from mkdocs_exporter.themes.material.theme import Theme as MaterialTheme
from mkdocs_exporter.themes.readthedocs.theme import Theme as ReadTheDocsTheme


class Factory:
  """The theme factory."""

  themes: 'list[Theme]' = [MaterialTheme, ReadTheDocsTheme]
  """The themes that are available."""


  @classmethod
  def create(self, theme: BaseTheme):
    """Creates a theme instance."""

    for t in self.themes:
      if t.name == theme.name:
        return t(theme)

    raise RuntimeError(f'The theme you are using ({theme.name}) is currently not supported by MkDocs Exporter, sorry.')
