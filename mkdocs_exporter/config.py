from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class Config(BaseConfig):
  """The plugin's configuration."""

  theme = c.Optional(c.Theme(default=None))
  """Override the theme used by your MkDocs instance."""
