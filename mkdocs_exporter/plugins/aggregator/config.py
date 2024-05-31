from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class Config(BaseConfig):
  """The plugin's configuration."""

  enabled = c.Type(bool, default=True)
  """Is the plugin enabled?"""

  stylesheets = c.ListOfItems(c.File(exists=True), default=[])
  """A list of custom stylesheets to apply before rendering documents."""

  scripts = c.ListOfItems(c.File(exists=True), default=[])
  """A list of custom scripts to inject before rendering documents."""
