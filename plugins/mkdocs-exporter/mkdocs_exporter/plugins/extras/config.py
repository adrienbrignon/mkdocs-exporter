from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class Config(BaseConfig):
  """The plugin's configuration."""

  downloads = c.ListOfItems(c.Choice(('pdf', 'html')), default=['pdf'])
  """The download buttons to show."""
