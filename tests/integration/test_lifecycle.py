"""End-to-end tests of the plugin's lifecycle and error handling."""

from __future__ import annotations

import asyncio
import logging
import re

import pytest
from mkdocs.exceptions import Abort

from tests.conftest import Project, Site

pytestmark = pytest.mark.browser

FAILING_PAGE = """
window.MkDocsExporter = {
  before: () => location.pathname.includes('reference') ? new Promise(() => {}) : null,
};
"""


def test_consecutive_builds_in_the_same_process(project: Project) -> None:
    """`mkdocs serve` rebuilds the site in the same process (#47)."""

    project.build()
    site = project.build()

    assert "combined.pdf" in site.pdfs()


def test_build_inside_a_running_event_loop(project: Project) -> None:
    """The plugin doesn't conflict with an event loop run by the caller (#45)."""

    async def main() -> Site:
        return project.build()

    site = asyncio.run(main())

    assert "combined.pdf" in site.pdfs()


def test_documents_are_not_generated_while_serving_by_default(
    project: Project, exporter_logs
) -> None:
    site = project.serve(builds=1)

    assert site.pdfs() == []
    assert any("not generated while serving" in m for m in exporter_logs())


def test_rebuilds_while_serving(project: Project) -> None:
    """The plugin instance is kept across rebuilds and resets its state (#47, #49)."""

    site = project.serve(builds=3, exporter={"formats": {"pdf": {"serve": True}}})

    assert "combined.pdf" in site.pdfs()
    assert site.pdf("combined.pdf").count("FRONT-COVER") == 4


def test_dirty_rebuilds_while_serving(project: Project) -> None:
    """Pages skipped by dirty rebuilds don't break the aggregator (#48)."""

    site = project.serve(
        builds=2, dirty=True, exporter={"formats": {"pdf": {"serve": True}}}
    )

    assert "combined.pdf" in site.pdfs()


def test_a_failing_page_does_not_prevent_others_from_rendering(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    project.write("scripts/fail.js", FAILING_PAGE)

    with pytest.raises(Abort):
        project.build(
            exporter={
                "formats": {
                    "pdf": {
                        "scripts": ["scripts/fail.js"],
                        "browser": {"timeout": 3000},
                    }
                }
            }
        )

    assert re.search(r"- reference\.md: Timed out after 3000 ms", caplog.text)
    assert (project.path / "site" / "index.pdf").exists()
    assert not (project.path / "site" / "reference" / "index.pdf").exists()


def test_timeouts_are_reported_with_diagnostics(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    project.write(
        "scripts/hang.js",
        "window.MkDocsExporter = { before: () => new Promise(() => {}) };",
    )

    with pytest.raises(Abort):
        project.build(
            exporter={
                "formats": {
                    "pdf": {
                        "scripts": ["scripts/hang.js"],
                        "browser": {"timeout": 2000},
                    }
                }
            },
        )

    assert "- index.md: Timed out after 2000 ms" in caplog.text


def test_script_errors_do_not_prevent_rendering(
    project: Project, exporter_logs
) -> None:
    project.write("scripts/broken.js", "throw new Error('broken script');")

    site = project.build(
        exporter={"formats": {"pdf": {"scripts": ["scripts/broken.js"]}}}
    )

    assert "index.pdf" in site.pdfs()
    assert exporter_logs(logging.WARNING) == []


def test_hook_errors_are_reported(project: Project, exporter_logs) -> None:
    project.write(
        "scripts/hook.js",
        "window.MkDocsExporter = { render: () => { throw new Error('hook failure'); } };",
    )

    site = project.build(
        exporter={"formats": {"pdf": {"scripts": ["scripts/hook.js"]}}}
    )

    assert "index.pdf" in site.pdfs()
    assert any("hook failure" in m for m in exporter_logs(logging.WARNING))


def test_missing_resources_are_reported(project: Project, exporter_logs) -> None:
    project.write("docs/reference.md", "# Reference\n\n![Missing](missing.png)\n")

    project.build()

    warnings = exporter_logs(logging.WARNING)

    assert any("reference.md" in m and "missing.png" in m for m in warnings)


def test_explicit_mode_without_pages_warns(project: Project, exporter_logs) -> None:
    site = project.build(exporter={"formats": {"pdf": {"explicit": True}}})

    assert site.pdfs() == []
    assert any("explicit mode" in m for m in exporter_logs(logging.WARNING))


def test_duplicate_navigation_entries(project: Project) -> None:
    """Pages listed twice in the navigation are aggregated once (#51)."""

    site = project.build(nav=["index.md", "reference.md", {"Again": "reference.md"}])

    assert site.pdf("combined.pdf").count("Plain reference page") == 1


def test_pages_outside_the_navigation(project: Project) -> None:
    """Pages outside the navigation get a document but are not aggregated."""

    site = project.build(nav=["index.md"])

    assert "reference/index.pdf" in site.pdfs()
    assert "Plain reference page" not in site.pdf("combined.pdf").text
