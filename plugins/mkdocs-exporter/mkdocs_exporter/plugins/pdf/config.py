from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class Config(BaseConfig):
  """The plugin's configuration."""

  enabled = c.Type(bool, default=True)
  """Is the generator enabled?"""

  concurrency = c.Type(int, default=4)
  """The maximum number of concurrent PDF generation tasks."""

  stylesheets = c.Type(list, default=[])
  """A list of custom stylesheets to apply before rendering documents."""
