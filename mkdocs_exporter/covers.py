from __future__ import annotations

import os
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateError
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError
from mkdocs.structure.pages import Page


class CoverRenderer:
    """Renders cover page templates with Jinja.

    When the `macros` plugin is enabled, its environment is used: templates have access
    to its variables, macros and filters, like Markdown pages do.
    """

    def __init__(self, config: MkDocsConfig) -> None:
        self.config = config
        self.root = os.path.dirname(config.config_file_path or "")
        self.environment = Environment(  # noqa: S701 (templates and values are the project's)
            loader=FileSystemLoader(self.root or "."), keep_trailing_newline=True
        )

    def render(self, path: str, page: Page) -> str:
        """Renders a cover template for a page."""

        macros: Any = self.config.plugins.get("macros")

        try:
            with open(path, encoding="utf-8") as file:
                source = file.read()

            if macros is not None and hasattr(macros, "env"):
                environment = macros.env
                variables = {**macros.variables, **page.meta}
            else:
                environment = self.environment
                variables = {"extra": self.config.extra, **page.meta}

            variables.update(page=page, config=self.config)

            return environment.from_string(source).render(**variables)
        except (OSError, TemplateError) as error:
            raise PluginError(
                f"[mkdocs-exporter.pdf] Failed to render the cover page '{path}' "
                f"of '{page.file.src_uri}': {error}"
            ) from error

    def locations(self, defaults: dict[str, str | None], page: Page) -> dict[str, str]:
        """The cover templates of a page, by location (`front`, `back`)."""

        if "covers" in page.meta.get("hide", []):
            return {}

        overrides = {
            key: os.path.join(self.root, value)
            for key, value in (page.meta.get("covers") or {}).items()
            if value
        }

        return {
            key: path
            for key, path in {**defaults, **overrides}.items()
            if key in ("front", "back") and path
        }
