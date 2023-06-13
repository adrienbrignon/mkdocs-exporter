from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class BrowserConfig(BaseConfig):
  """The browser's configuration."""

  debug = c.Type(bool, default=False)
  """Should console messages sent to the browser be logged?"""


class CoversConfig(BaseConfig):
  """The cover's configuration."""

  front = c.Optional(c.File(exists=True))
  """The front cover template location."""

  back = c.Optional(c.File(exists=True))
  """The back cover template location."""


class Config(BaseConfig):
  """The plugin's configuration."""

  enabled = c.Type(bool, default=True)
  """Is the generator enabled?"""

  explicit = c.Type(bool, default=False)
  """Should pages specify explicitly that they should be rendered as PDF?"""

  concurrency = c.Type(int, default=4)
  """The maximum number of concurrent PDF generation tasks."""

  stylesheets = c.ListOfItems(c.File(exists=True), default=[])
  """A list of custom stylesheets to apply before rendering documents."""

  scripts = c.ListOfItems(c.File(exists=True), default=[])
  """A list of custom scripts to inject before rendering documents."""

  covers = c.SubConfig(CoversConfig)
  """The document's cover pages."""

  browser = c.SubConfig(BrowserConfig)
  """The browser's configuration."""
