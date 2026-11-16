from __future__ import annotations

import logging

import pytest
from mkdocs.exceptions import Abort

from tests.conftest import Project

pytestmark = pytest.mark.browser


def test_the_exporter_key_takes_precedence_over_deprecated_keys(
    project: Project,
) -> None:
    project.write(
        "docs/reference.md",
        "---\nhide: [covers]\nexporter: {pdf: {covers: {enabled: true}}}\n---\n\n"
        "# Reference\n",
    )

    document = project.build().pdf("reference/index.pdf")

    assert document.count("FRONT-COVER") == 1
    assert document.count("BACK-COVER") == 1


def test_deprecated_keys_are_reported_once_per_key_and_build(
    project: Project, exporter_logs
) -> None:
    project.write(
        "docs/reference.md", "---\npdf: true\ntoc: false\n---\n\n# Reference\n"
    )
    project.write("docs/guide/intro.md", "---\npdf: true\n---\n\n# Introduction\n")

    project.serve(builds=2, exporter={"formats": {"pdf": {"serve": True}}})
    warnings = exporter_logs(logging.WARNING)

    assert (
        sum("'pdf' key of the front matter is deprecated" in m for m in warnings) == 2
    )
    assert (
        sum("'toc' key of the front matter is deprecated" in m for m in warnings) == 2
    )
    assert all("exporter.pdf" in m for m in warnings)


def test_invalid_options_fail_the_build(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    project.write(
        "docs/reference.md",
        "---\nexporter: {pdf: {enable: false}}\n---\n\n# Reference\n",
    )

    with pytest.raises(Abort):
        project.build()

    assert "Invalid front matter in 'reference.md': exporter.pdf:" in caplog.text
    assert "'enable'" in caplog.text


def test_options_can_come_from_meta_files(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Material for MkDocs' `meta` plugin merges `.meta.yml` into the front matter of
    the pages of its directory (before the exporter reads it).

    The project is built from its directory, like with `mkdocs build`: the plugin
    finds `docs_dir` relative to the working directory, which fails on Windows when
    they're on different drives.
    """

    monkeypatch.chdir(project.path)
    project.write("docs/guide/.meta.yml", "exporter:\n  pdf:\n    enabled: false\n")
    project.write(
        "docs/guide/intro.md",
        "---\nexporter: {pdf: {covers: {enabled: false}}}\n---\n\n# Introduction\n",
    )

    site = project.build(plugins=["meta"])

    assert "guide/intro/index.pdf" not in site.pdfs()
    assert "guide/advanced/index.pdf" not in site.pdfs()
    assert "reference/index.pdf" in site.pdfs()


def test_pages_can_add_buttons(project: Project) -> None:
    project.write(
        "docs/reference.md",
        "---\nexporter:\n  buttons:\n    - title: PAGE-BUTTON\n"
        "      icon: material-star-outline\n"
        "      attributes: {href: 'https://example.org/'}\n---\n\n# Reference\n",
    )

    site = project.build()

    assert 'title="PAGE-BUTTON"' in site.html("reference/index.html")
    assert 'title="PAGE-BUTTON"' not in site.html("index.html")
