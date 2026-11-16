from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mkdocs.exceptions import PluginError

from mkdocs_exporter.covers import CoverRenderer


def page(title: str, **meta: str) -> Any:
    """A minimal stand-in for a MkDocs page."""

    return SimpleNamespace(
        title=title, meta=meta, file=SimpleNamespace(src_uri="index.md")
    )


def renderer(root: Path) -> CoverRenderer:
    """The cover renderer of a build (without the macros plugin)."""

    config: Any = SimpleNamespace(
        config_file_path=str(root / "mkdocs.yml"), plugins={}, extra={}
    )

    return CoverRenderer(config)


def test_templates_are_compiled_once_per_build(tmp_path: Path) -> None:
    template = tmp_path / "front.html"
    template.write_text("<h1>{{ page.title }} by {{ author }}</h1>")
    covers = renderer(tmp_path)

    assert covers.render(str(template), page("A", author="Ada")) == "<h1>A by Ada</h1>"

    template.write_text("CHANGED")

    assert covers.render(str(template), page("B", author="Bob")) == "<h1>B by Bob</h1>"
    assert renderer(tmp_path).render(str(template), page("B")) == "CHANGED"


def test_missing_templates_fail_the_build(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match="Failed to render the cover page"):
        renderer(tmp_path).render(str(tmp_path / "missing.html"), page("A"))
