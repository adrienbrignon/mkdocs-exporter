from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class BrowserConfig(BaseConfig):
  """The browser's configuration."""

  debug = c.Type(bool, default=False)
  """Should console messages sent to the browser be logged?"""

  headless = c.Type(bool, default=True)
  """Should the browser start in headless mode?"""

  timeout = c.Type(int, default=60_000)
  """The timeout when waiting for the PDF to render."""

  args = c.ListOfItems(c.Type(str), default=[])
  """Extra arguments to pass to the browser."""


class CoversConfig(BaseConfig):
  """The cover's configuration."""

  front = c.Optional(c.File(exists=True))
  """The front cover template location."""

  back = c.Optional(c.File(exists=True))
  """The back cover template location."""


class AggregatorConfig(BaseConfig):
  """The aggregator's configuration."""

  enabled = c.Type(bool, default=False)
  """Is the aggregator enabled?"""

  output = c.Type(str, default='combined.pdf')
  """The aggregated PDF document output file path."""

  metadata = c.Type(dict, default={})
  """Some metadata to append to the PDF document."""

  covers = c.Choice(['all', 'none', 'limits', 'book', 'front', 'back'], default='all')
  """The behavior of cover pages."""


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

  url = c.Optional(c.Type(str))
  """The base URL that'll be prefixed to links with a relative path."""

  aggregator = c.SubConfig(AggregatorConfig)
  """The aggregator's configuration."""
