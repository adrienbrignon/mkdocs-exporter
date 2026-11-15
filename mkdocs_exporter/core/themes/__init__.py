from __future__ import annotations

from mkdocs_exporter.core.themes.base import Theme
from mkdocs_exporter.core.themes.material import MaterialTheme
from mkdocs_exporter.core.themes.readthedocs import ReadTheDocsTheme

THEMES: dict[str, type[Theme]] = {
    "material": MaterialTheme,
    "materialx": MaterialTheme,
    "readthedocs": ReadTheDocsTheme,
}
"""The themes with dedicated support, by name."""


def get_theme(name: str | None) -> Theme:
    """Returns the adapter of a theme (a generic one for unknown themes)."""

    return THEMES.get(name or "", Theme)()


__all__ = ["THEMES", "MaterialTheme", "ReadTheDocsTheme", "Theme", "get_theme"]
