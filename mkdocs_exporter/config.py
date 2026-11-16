from collections.abc import Callable
from typing import cast

from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig

from mkdocs_exporter.formats.pdf.config import Config as PDFFormatConfig


class FormatsConfig(BaseConfig):
    """The formats of documents (`formats`)."""

    pdf = c.SubConfig(PDFFormatConfig)
    """PDF documents."""


CALLABLE = cast(type, Callable)
"""Any callable (`typing` special forms are not types for type checkers)."""


class ButtonConfig(BaseConfig):
    """A button added at the top of pages (`buttons[]`): each option can be a callable
    computing it from the page."""

    enabled = c.Type((bool, CALLABLE), default=True)
    """Is the button enabled?"""

    title = c.Type((str, CALLABLE))
    """The button's title (its tooltip with Material for MkDocs, its text with other
    themes)."""

    icon = c.Type((str, CALLABLE))
    """The name of a Material for MkDocs icon (e.g. `material-file-download-outline`);
    other themes don't show icons."""

    attributes = c.Type((dict, CALLABLE), default={})
    """Attributes of the button's link (e.g. `href`, `target`, `download`; `class`
    replaces the theme's classes)."""


class LoggingConfig(BaseConfig):
    """The messages logged by the plugin (`logging`)."""

    level = c.Choice(["debug", "info", "warning", "error", "critical"], default="info")
    """The log level."""


class Config(BaseConfig):
    """The options of the plugin (`plugins: - exporter:`)."""

    theme = c.Optional(c.Theme(default=None))
    """The theme whose adjustments are applied to documents (the website's theme by
    default), e.g. `material` for a theme derived from Material for MkDocs."""

    formats = c.SubConfig(FormatsConfig)
    """The formats of documents."""

    buttons = c.ListOfItems(c.SubConfig(ButtonConfig), default=[])
    """Buttons added at the top of every page."""

    logging = c.SubConfig(LoggingConfig)
    """The messages logged by the plugin."""
