from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, TemplateError
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError

from mkdocs_exporter.adapter import PageLike
from mkdocs_exporter.front_matter import CoversOptions


class CoverRenderer:
    """Renders cover page templates with Jinja.

    When the `macros` plugin is enabled, its environment is used: templates have access
    to its variables, macros and filters, like Markdown pages do.
    """

    def __init__(
        self, root: str, extra: Mapping[str, Any], config: Any, macros: Any = None
    ) -> None:
        """
        Args:
            root: The directory of the configuration file (paths are relative to it).
            extra: The `extra` settings of the website.
            config: The configuration of the website (`config` in templates).
            macros: The macros plugin, when enabled.
        """

        self.root = root
        self.extra = extra
        self.config = config
        self.macros = macros
        self.environment = Environment(  # noqa: S701 (templates and values are the project's)
            loader=FileSystemLoader(self.root or "."), keep_trailing_newline=True
        )
        self.templates: dict[tuple[Environment, str], Template] = {}
        """The templates compiled so far, by environment and path (compiling a template
        takes up to a few milliseconds, rendering it a few microseconds)."""

    @classmethod
    def of(cls, config: MkDocsConfig) -> CoverRenderer:
        """The cover renderer of a MkDocs website."""

        return cls(
            os.path.dirname(config.config_file_path or ""),
            config.extra,
            config,
            config.plugins.get("macros"),
        )

    def render(self, path: str, page: PageLike) -> str:
        """Renders a cover template for a page."""

        macros = self.macros

        try:
            if macros is not None and hasattr(macros, "env"):
                environment = macros.env
                variables = {**macros.variables, **page.meta}
            else:
                environment = self.environment
                variables = {"extra": self.extra, **page.meta}

            variables.update(page=page, config=self.config)

            return self._template(environment, path).render(**variables)
        except (OSError, TemplateError) as error:
            raise PluginError(
                f"[mkdocs-exporter.pdf] Failed to render the cover page '{path}' "
                f"of '{page.file.src_uri}': {error}"
            ) from error

    def _template(self, environment: Environment, path: str) -> Template:
        """A template, compiled once per environment."""

        key = (environment, path)

        if key not in self.templates:
            with open(path, encoding="utf-8") as file:
                self.templates[key] = environment.from_string(file.read())

        return self.templates[key]

    def locations(
        self, defaults: dict[str, str | None], covers: CoversOptions
    ) -> dict[str, str]:
        """The cover templates of a page, by location (`front`, `back`), given the
        options of its front matter."""

        if covers.enabled is False:
            return {}

        overrides = {
            key: os.path.join(self.root, value)
            for key in ("front", "back")
            if (value := covers[key])
        }

        return {
            key: path
            for key, path in {**defaults, **overrides}.items()
            if key in ("front", "back") and path
        }
