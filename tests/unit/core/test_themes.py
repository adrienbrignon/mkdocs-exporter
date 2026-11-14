"""Tests of the theme adapters."""

import pytest

from mkdocs_exporter.core.themes import (
    MaterialTheme,
    ReadTheDocsTheme,
    Theme,
    get_theme,
)
from mkdocs_exporter.core.themes.base import fix_nth_selectors


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("material", MaterialTheme),
        ("materialx", MaterialTheme),
        ("readthedocs", ReadTheDocsTheme),
        ("mkdocs", Theme),
        (None, Theme),
    ],
)
def test_get_theme(name: str | None, kind: type[Theme]) -> None:
    assert type(get_theme(name)) is kind


@pytest.mark.parametrize(
    ("css", "expected"),
    [
        (":nth-of-type(3n+1)", ":nth-of-type(3n-2)"),
        (":nth-child(2n + 1)", ":nth-child(2n-1)"),
        (":nth-last-child(4n+3)", ":nth-last-child(4n-1)"),
        (":nth-child(n+3)", ":nth-child(n+3)"),
        (":nth-child(2n+2)", ":nth-child(2n+2)"),
        (":nth-child(odd)", ":nth-child(odd)"),
    ],
)
def test_fix_nth_selectors(css: str, expected: str) -> None:
    assert fix_nth_selectors(css) == expected


def test_material_icons() -> None:
    pytest.importorskip("material")

    assert (MaterialTheme().icon("material-file-download-outline") or "").startswith(
        "<svg"
    )
    assert MaterialTheme().icon("material-does-not-exist") is None
