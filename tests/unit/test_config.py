"""Tests of the plugin's configuration schema."""

from pathlib import Path

import pytest

from mkdocs_exporter.plugin import Plugin


def load(tmp_path: Path, options: dict) -> tuple[list, list]:
    """Validates some plugin options, returning errors and warnings."""

    config_file = tmp_path / "mkdocs.yml"
    config_file.touch()

    return Plugin().load_config(options, config_file_path=str(config_file))


@pytest.mark.parametrize("name", ["pdf.scss", "pdf.SASS"])
def test_sass_stylesheets_are_rejected(tmp_path: Path, name: str) -> None:
    (tmp_path / name).touch()

    errors, _ = load(tmp_path, {"formats": {"pdf": {"stylesheets": [name]}}})

    assert len(errors) == 1
    assert "Sass stylesheets are no longer supported" in str(errors[0][1])


def test_css_stylesheets_are_accepted(tmp_path: Path) -> None:
    (tmp_path / "pdf.css").touch()

    errors, _ = load(tmp_path, {"formats": {"pdf": {"stylesheets": ["pdf.css"]}}})

    assert errors == []


def test_missing_stylesheets_are_rejected(tmp_path: Path) -> None:
    errors, _ = load(tmp_path, {"formats": {"pdf": {"stylesheets": ["missing.css"]}}})

    assert len(errors) == 1


def test_defaults(tmp_path: Path) -> None:
    plugin = Plugin()
    config_file = tmp_path / "mkdocs.yml"
    config_file.touch()

    errors, _ = plugin.load_config({}, config_file_path=str(config_file))

    assert errors == []
    assert plugin.config.buttons == []
    assert plugin.config.formats.pdf.enabled is True
    assert plugin.config.formats.pdf.explicit is False
