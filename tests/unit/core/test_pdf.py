"""Tests of the PDF post-processing helpers."""

import pytest

from mkdocs_exporter.core.pdf import relative_url


@pytest.mark.parametrize(
    ("target", "directory", "expected"),
    [
        ("guide/intro/", "", "guide/intro/"),
        ("", "guide/intro", "../../"),
        ("", "", "./"),
        ("guide/advanced/#deep-dive", "guide/intro", "../advanced/#deep-dive"),
        ("guide/intro/", "guide/intro", "./"),
        ("index.html", "guide", "../index.html"),
        ("guide/intro.html?x=1", "guide", "intro.html?x=1"),
    ],
)
def test_relative_url(target: str, directory: str, expected: str) -> None:
    assert relative_url(target, directory) == expected
