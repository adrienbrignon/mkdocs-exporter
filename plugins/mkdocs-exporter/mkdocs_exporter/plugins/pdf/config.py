from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class Config(BaseConfig):
  """The plugin's configuration."""

  enabled = c.Type(bool, default=True)
  """Is the generator enabled?"""

  stylesheets = c.Type(list, default=[])
  """A list of custom stylesheets to apply before rendering documents."""
