from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from mkdocs.exceptions import ConfigurationError
from mkdocs.utils.yaml import get_yaml_loader, yaml_load

from mkdocs_exporter.adapter import Website
from mkdocs_exporter.config import Config

CONFIG_FILES = ("zensical.toml", "mkdocs.yml", "mkdocs.yaml")
"""The configuration files of a website, in the order Zensical looks for them."""

META_PLUGINS = ("meta", "material/meta")
"""The names of the plugin applying `.meta.yml` files to the pages of a directory."""


class ProjectError(Exception):
    """A website can't be exported (its configuration is missing or invalid)."""


@dataclass
class Project:
    """A built website, and the exporter's options from its configuration."""

    config_file: Path
    """The configuration file of the website."""

    settings: dict[str, Any]
    """The settings of the website (`config` in cover templates)."""

    options: Config
    """The exporter's options (`plugins: - exporter:` or `[project.plugins.exporter]`)."""

    ignored: list[str] = field(default_factory=list)
    """The options the command doesn't support (left out of `options`)."""

    @property
    def root(self) -> Path:
        """The directory of the configuration file (paths are relative to it)."""

        return self.config_file.parent

    @property
    def site_dir(self) -> Path:
        """The directory of the built website."""

        return self.root / str(self.settings.get("site_dir") or "site")

    @property
    def docs_dir(self) -> Path:
        """The directory of the website's sources."""

        return self.root / str(self.settings.get("docs_dir") or "docs")

    @property
    def use_directory_urls(self) -> bool:
        """Are pages built as `page/index.html` (rather than `page.html`)?"""

        return bool(self.settings.get("use_directory_urls", True))

    @property
    def nav(self) -> list[Any] | None:
        """The navigation of the configuration, if any."""

        nav = self.settings.get("nav")

        return nav if isinstance(nav, list) and nav else None

    @property
    def meta_file(self) -> str | None:
        """The name of the files giving defaults to the front matter of the pages of
        their directory, when the `meta` plugin is enabled."""

        for name in META_PLUGINS:
            plugin = _plugins(self.settings).get(name)

            if name in _plugins(self.settings) and (plugin or {}).get("enabled", True):
                return str((plugin or {}).get("meta_file") or ".meta.yml")

        return None

    @property
    def website(self) -> Website:
        """The settings of the website the exporter uses."""

        settings = self.settings

        return Website(
            name=str(settings.get("site_name") or ""),
            url=settings.get("site_url") or None,
            author=settings.get("site_author"),
            description=settings.get("site_description"),
            extra=settings.get("extra") or {},
        )


def find(directory: Path) -> Path:
    """The configuration file of the website in a directory."""

    for name in CONFIG_FILES:
        if (directory / name).is_file():
            return directory / name

    raise ProjectError(
        f"No configuration file found in '{directory}' "
        f"(looked for {', '.join(CONFIG_FILES)})"
    )


def load(config_file: Path | None = None) -> Project:
    """Loads a website's configuration and the exporter's options from it.

    Args:
        config_file: The configuration file (found in the current directory if not
            given).

    Raises:
        ProjectError: When the configuration is missing or invalid.
    """

    path = (config_file or find(Path.cwd())).resolve()

    try:
        settings = _read(path)
    except (OSError, ValueError, ConfigurationError) as error:
        raise ProjectError(f"Can't read '{path}': {error}") from error

    raw = dict(_plugins(settings).get("exporter") or {})
    ignored = [key for key in ("buttons",) if raw.pop(key, None)]
    options = Config(config_file_path=str(path))
    options.load_dict(raw)
    failed, warnings = options.validate()
    problems = [f"{key}: {message}" for key, message in [*failed, *warnings]]

    if problems:
        raise ProjectError(
            f"Invalid options of the exporter in '{path}': " + "; ".join(problems)
        )

    return Project(
        config_file=path, settings=settings, options=options, ignored=ignored
    )


def _read(path: Path) -> dict[str, Any]:
    """The settings of a configuration file (the `project` table of TOML files)."""

    if path.suffix == ".toml":
        with path.open("rb") as file:
            data = tomllib.load(file)

        project = data.get("project", data)
    else:
        with path.open(encoding="utf-8") as file:
            project = yaml_load(file, _Loader) or {}

    if not isinstance(project, dict):
        raise ValueError("expected a mapping of settings")

    return project


class Unresolved(str):
    """A value of a configuration file the command can't resolve (e.g. a Python object
    of a package that isn't installed): it keeps its tag and value."""


class _Loader(get_yaml_loader()):  # type: ignore[misc]
    """Loads configuration files like MkDocs (`!ENV`, `INHERIT`), resolving the tags it
    can: only the settings the exporter uses matter (Python objects, such as Material's
    emoji functions, may belong to packages that aren't installed)."""

    def construct_python_name(self, suffix: str, node: Any) -> Any:
        try:
            return super().construct_python_name(suffix, node)
        except yaml.constructor.ConstructorError:
            return Unresolved(f"!!python/name:{suffix}")

    def construct_unknown(self, node: Any) -> Any:
        value = self.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else ""

        return Unresolved(f"{node.tag} {value}".strip())


_Loader.add_multi_constructor(
    "tag:yaml.org,2002:python/name:", _Loader.construct_python_name
)
_Loader.add_constructor(None, _Loader.construct_unknown)


def _plugins(settings: Mapping[str, Any]) -> dict[str, Any]:
    """The plugins of a configuration, by name: a list of names or single-key
    mappings (YAML), or a mapping (YAML or TOML)."""

    plugins = settings.get("plugins") or {}

    if isinstance(plugins, Mapping):
        return dict(plugins)

    result: dict[str, Any] = {}

    for item in plugins if isinstance(plugins, list) else []:
        if isinstance(item, str):
            result[item] = {}
        elif isinstance(item, Mapping):
            result.update(item)

    return result
