import pytest

from mkdocs_exporter.core.themes import (
    MaterialTheme,
    ReadTheDocsTheme,
    Theme,
    get_theme,
)


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


def test_material_icons() -> None:
    pytest.importorskip("material")

    assert (MaterialTheme().icon("material-file-download-outline") or "").startswith(
        "<svg"
    )
    assert MaterialTheme().icon("material-does-not-exist") is None
