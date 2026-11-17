from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig

from mkdocs_exporter.config import ButtonConfig

KEY = "exporter"
"""The front matter key holding the options of a page."""

DEPRECATED = {
    "pdf": "exporter.pdf.enabled",
    "covers": "exporter.pdf.covers.front and exporter.pdf.covers.back",
    "hide": "exporter.pdf.covers.enabled: false",
    "toc": "exporter.pdf.toc.enabled",
    "buttons": "exporter.buttons",
    "pdf-icon": "the icon of the download button in buttons",
}
"""The front matter keys replaced by `exporter`, and what replaces them (`hide` only
when it lists `covers`)."""


class CoversOptions(BaseConfig):
    """The cover pages of a page's document."""

    enabled = c.Optional(c.Type(bool))
    """`false` leaves the document without cover pages."""

    front = c.Optional(c.Type(str))
    """A template replacing the front cover (relative to the configuration file)."""

    back = c.Optional(c.Type(str))
    """A template replacing the back cover (relative to the configuration file)."""


class TocOptions(BaseConfig):
    """The table of contents of a page's document."""

    enabled = c.Optional(c.Type(bool))
    """Overrides `formats.pdf.toc.enabled`."""


class PdfOptions(BaseConfig):
    """The PDF document of a page."""

    enabled = c.Optional(c.Type(bool))
    """`false` leaves the page without a document; `true` gives it one in explicit mode."""

    covers = c.SubConfig(CoversOptions)
    toc = c.SubConfig(TocOptions)


class PageOptions(BaseConfig):
    """The options of a page, from the `exporter` key of its front matter (each unset
    option keeps the value of the configuration)."""

    pdf = c.SubConfig(PdfOptions)
    buttons = c.ListOfItems(c.SubConfig(ButtonConfig), default=[])
    """Buttons added to the page, besides those of the configuration."""


class FrontMatterError(ValueError):
    """The `exporter` key of a page's front matter is invalid."""


@dataclass
class Parsed:
    """The options of a page and the deprecated keys it uses."""

    options: PageOptions
    deprecated: list[str] = field(default_factory=list)


def parse(meta: Mapping[str, Any]) -> Parsed:
    """The options of a page, from its front matter.

    The keys replaced by `exporter` keep working as before (their values are coerced,
    not validated); `exporter` takes precedence over them, option by option.

    Raises:
        FrontMatterError: When the `exporter` key is invalid.
    """

    deprecated = [key for key in DEPRECATED if _uses(meta, key)]

    if not deprecated and KEY not in meta:
        return Parsed(options=_defaults())

    options = PageOptions()
    options.load_dict(_merge(_legacy(meta), _namespaced(meta)))
    failed, warnings = options.validate()
    problems = [f"{KEY}.{key}: {message}" for key, message in [*failed, *warnings]]

    if problems:
        raise FrontMatterError("; ".join(problems))

    return Parsed(options=options, deprecated=deprecated)


@cache
def _defaults() -> PageOptions:
    """The options of pages that set none (shared: they're never modified)."""

    options = PageOptions()
    options.load_dict({})
    options.validate()

    return options


def _uses(meta: Mapping[str, Any], key: str) -> bool:
    """Does the front matter use a deprecated key?"""

    if key == "hide":
        return _hides_covers(meta)

    return key in meta


def _hides_covers(meta: Mapping[str, Any]) -> bool:
    """Does `hide` list `covers` (like v6, which also accepted a string)?"""

    try:
        return "covers" in (meta.get("hide") or [])
    except TypeError:
        return False


def _legacy(meta: Mapping[str, Any]) -> dict[str, Any]:
    """The options given by the deprecated keys, coerced like v6 did."""

    pdf: dict[str, Any] = {}
    covers: dict[str, Any] = {}

    if "pdf" in meta:
        pdf["enabled"] = bool(meta["pdf"])
    if "toc" in meta:
        pdf["toc"] = {"enabled": bool(meta["toc"])}
    if isinstance(meta.get("covers"), Mapping):
        covers.update(
            (key, str(value))
            for key, value in meta["covers"].items()
            if key in ("front", "back") and value
        )
    if _hides_covers(meta):
        covers["enabled"] = False
    if covers:
        pdf["covers"] = covers

    raw: dict[str, Any] = {"pdf": pdf} if pdf else {}

    if isinstance(meta.get("buttons"), list):
        raw["buttons"] = meta["buttons"]

    return raw


def _namespaced(meta: Mapping[str, Any]) -> dict[str, Any]:
    """The options of the `exporter` key (empty when it is empty)."""

    value = meta.get(KEY)

    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise FrontMatterError(
            f"{KEY}: expected a mapping of options, but received: {type(value).__name__}"
        )

    return copy.deepcopy(dict(value))


def _merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Merges options key by key (mappings are merged, other values replaced)."""

    result = dict(base)

    for key, value in overrides.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge(dict(result[key]), dict(value))
        else:
            result[key] = value

    return result
