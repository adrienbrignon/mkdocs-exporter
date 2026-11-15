from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import Any

LOGGER = logging.getLogger("mkdocs.plugins.mkdocs_exporter")
"""The logger of the exporter, under MkDocs' (whose `--strict` mode counts warnings)."""


class Logger(logging.LoggerAdapter[logging.Logger]):
    """Logs messages prefixed with the part of the exporter they come from (e.g.
    `[mkdocs-exporter.pdf]`)."""

    def __init__(self, area: str = "") -> None:
        super().__init__(LOGGER)

        self.prefix = f"[mkdocs-exporter{f'.{area}' if area else ''}] "

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        return self.prefix + str(msg), kwargs


logger = Logger()
"""Logs messages about the exporter as a whole."""
