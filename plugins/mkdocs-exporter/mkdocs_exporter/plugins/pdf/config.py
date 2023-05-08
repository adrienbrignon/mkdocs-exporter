from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class CoversConfig(BaseConfig):
  """The cover's configuration."""

  front = c.Optional(c.Type(str))
  """The front cover template location."""

  back = c.Optional(c.Type(str))
  """The back cover template location."""


class Config(BaseConfig):
  """The plugin's configuration."""

  enabled = c.Type(bool, default=True)
  """Is the generator enabled?"""

  concurrency = c.Type(int, default=4)
  """The maximum number of concurrent PDF generation tasks."""

  stylesheets = c.ListOfItems(c.Type(str), default=[])
  """A list of custom stylesheets to apply before rendering documents."""

  scripts = c.ListOfItems(c.Type(str), default=[])
  """A list of custom scripts to inject before rendering documents."""

  covers = c.SubConfig(CoversConfig)
  """The document's cover pages."""

  polyfills = c.Type(bool, default=True)
  """Should polyfills be imported?"""
