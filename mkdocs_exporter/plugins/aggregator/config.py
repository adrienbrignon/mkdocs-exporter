from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class Config(BaseConfig):
  """The plugin's configuration."""

  enabled = c.Type(bool, default=True)
  """Is the plugin enabled?"""

  metadata = c.Type(dict, default={})
  """The metadata to append to the PDF."""

  output = c.Type(str, default='site.pdf')
  """The output file path."""

  covers = c.Choice(['all', 'none', 'limits'], default='all')
  """The way that cover pages will be handled."""
