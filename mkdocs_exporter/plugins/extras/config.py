from typing import Callable
from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig


class ButtonConfig(BaseConfig):
  """The configuration of a button."""

  title = c.Type((str, Callable))
  """The button's title."""

  icon = c.Type((str, Callable))
  """The button's icon (typically, an SVG element)."""

  href = c.Type((str, Callable))
  """The button's 'href' attribute."""

  download = c.Optional(c.Type((bool, str, Callable)))
  """The button's 'download' attribute."""

  target = c.Optional(c.Choice(('_blank', '_self', '_parent', '_top')))
  """The button's 'target' attribute."""


class Config(BaseConfig):
  """The plugin's configuration."""

  downloads = c.ListOfItems(c.Choice(('pdf', 'html')), default=['pdf'])
  """The download buttons to show."""

  buttons = c.ListOfItems(c.SubConfig(ButtonConfig))
  """The buttons to add."""
