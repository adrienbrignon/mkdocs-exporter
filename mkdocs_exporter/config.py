from collections.abc import Callable
from typing import cast

from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig

from mkdocs_exporter.formats.pdf.config import Config as PDFFormatConfig


class FormatsConfig(BaseConfig):
    pdf = c.SubConfig(PDFFormatConfig)
    """The PDF format configuration."""


CALLABLE = cast(type, Callable)
"""Any callable (`typing` special forms are not types for type checkers)."""


class ButtonConfig(BaseConfig):
    """The configuration of a button."""

    enabled = c.Type((bool, CALLABLE), default=True)
    """Is the button enabled?"""

    title = c.Type((str, CALLABLE))
    """The button's title."""

    icon = c.Type((str, CALLABLE))
    """The button's icon (typically, an SVG element)."""

    attributes = c.Type((dict, CALLABLE), default={})
    """Some extra attributes to add to the button."""


class LoggingConfig(BaseConfig):
    """The logging configuration."""

    level = c.Choice(["debug", "info", "warning", "error", "critical"], default="info")
    """The log level."""


class Config(BaseConfig):
    """The plugin's configuration."""

    theme = c.Optional(c.Theme(default=None))
    """Override the theme used by your MkDocs instance."""

    formats = c.SubConfig(FormatsConfig)
    """The formats to generate."""

    buttons = c.ListOfItems(c.SubConfig(ButtonConfig), default=[])
    """The buttons to add."""

    logging = c.SubConfig(LoggingConfig)
    """The logging configuration."""
