"""Shared fixtures: build the fixture project with MkDocs and inspect the output."""

from __future__ import annotations

import copy
import logging
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import pytest

if os.environ.get("MKDOCS_EXPORTER_TEST_PROPERDOCS"):
    import properdocs.replacement  # noqa: F401  (redirects `mkdocs` imports to ProperDocs)

from mkdocs.commands.build import build
from mkdocs.config import load_config

from mkdocs_exporter.formats.pdf.buttons import download
from tests.support.pdf import PdfDocument

FIXTURES = Path(__file__).parent / "fixtures"

DEFAULT_EXPORTER: dict[str, Any] = {
    "formats": {
        "pdf": {
            "concurrency": 4,
            "stylesheets": ["pdf.css"],
            "covers": {"front": "covers/front.html", "back": "covers/back.html"},
            "browser": {"timeout": 30_000},
            "aggregator": {"enabled": True, "output": "combined.pdf"},
        },
    },
    "buttons": [
        {
            "title": "Download as PDF",
            "icon": "material-file-download-outline",
            "enabled": download.enabled,
            "attributes": download.attributes,
        },
    ],
}
"""The default options of the plugin used by the fixture project."""


def merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Deep-merges two dictionaries (a `None` value removes a key)."""

    result = copy.deepcopy(base)

    for key, value in overrides.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value

    return result


@cache
def browser_available() -> bool:
    """Whether Playwright can launch Chromium on this machine."""

    from playwright.sync_api import Error, sync_playwright

    try:
        with sync_playwright() as playwright:
            playwright.chromium.launch().close()
    except Error:
        return False

    return True


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skips browser tests when no browser is available (fails on CI instead)."""

    browser_items = [item for item in items if "browser" in item.keywords]

    if not browser_items or os.environ.get("CI") or browser_available():
        return

    marker = pytest.mark.skip(
        reason="Chromium is not installed (uv run playwright install chromium)"
    )

    for item in browser_items:
        item.add_marker(marker)


@dataclass
class Site:
    """A built site."""

    project: Path
    """The project directory."""

    path: Path
    """The output directory."""

    def pdf(self, path: str) -> PdfDocument:
        """Reads a PDF document from the output directory."""

        return PdfDocument(self.path / path)

    def pdfs(self) -> list[str]:
        """The PDF documents of the output directory (relative paths)."""

        return sorted(
            p.relative_to(self.path).as_posix() for p in self.path.rglob("*.pdf")
        )

    def html(self, path: str) -> str:
        """Reads an HTML file from the output directory."""

        return (self.path / path).read_text(encoding="utf-8")


class Project:
    """A copy of the fixture project that can be customized and built."""

    def __init__(self, path: Path) -> None:
        self.path = path

        shutil.copytree(FIXTURES / "site", path)

    def write(self, path: str, content: str) -> Project:
        """Writes a file inside the project."""

        target = self.path / path

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        return self

    def build(
        self,
        exporter: dict[str, Any] | None = None,
        plugins: list[Any] | None = None,
        **config: Any,
    ) -> Site:
        """Builds the project (like `mkdocs build` does)."""

        site_dir = self.path / "site"
        options = merge(DEFAULT_EXPORTER, exporter or {})
        cfg = load_config(
            config_file=str(self.path / "mkdocs.yml"),
            site_dir=str(site_dir),
            plugins=[*(plugins or []), {"exporter": options}],
            **config,
        )

        cfg.plugins.on_startup(command="build", dirty=False)

        try:
            build(cfg)
        finally:
            cfg.plugins.on_shutdown()

        return Site(project=self.path, path=site_dir)


@pytest.fixture
def project(tmp_path: Path) -> Project:
    """A fresh copy of the fixture project."""

    return Project(tmp_path / "project")


@pytest.fixture
def exporter_logs(caplog: pytest.LogCaptureFixture) -> Callable[..., list[str]]:
    """Messages logged by the plugin, optionally filtered by minimum level."""

    caplog.set_level(logging.DEBUG, logger="mkdocs")

    def messages(level: int = logging.DEBUG) -> list[str]:
        return [
            record.getMessage()
            for record in caplog.records
            if record.name.startswith("mkdocs.plugins.mkdocs_exporter")
            and record.levelno >= level
        ]

    return messages
