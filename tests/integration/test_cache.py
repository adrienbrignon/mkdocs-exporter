from __future__ import annotations

import pytest

from tests.conftest import Project, merge

pytestmark = pytest.mark.browser

PAGES = ["index.md", "guide/intro.md", "guide/advanced.md", "reference.md"]

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="{color}"/></svg>'

SINGLE = {"formats": {"pdf": {"books": []}}}
"""Without combined documents (their pages are rendered again, without the cache)."""


@pytest.fixture
def rendered(caplog: pytest.LogCaptureFixture):
    """The pages rendered since the last call (others were reused)."""

    def pages() -> list[str]:
        messages = [record.getMessage() for record in caplog.records]
        caplog.clear()

        return sorted(
            page for page in PAGES if f"Rendering '{page}'..." in "\n".join(messages)
        )

    caplog.set_level("DEBUG", logger="mkdocs")

    return pages


def test_unchanged_pages_are_reused(project: Project, rendered) -> None:
    first = project.build(SINGLE)
    texts = {path: first.pdf(path).text for path in first.pdfs()}

    assert rendered() == sorted(PAGES)
    assert (project.path / ".cache" / "plugin" / "exporter").is_dir()

    second = project.build(SINGLE)

    assert rendered() == []
    assert {path: second.pdf(path).text for path in second.pdfs()} == texts


def test_changed_pages_are_rendered_again(project: Project, rendered) -> None:
    project.build(SINGLE)
    rendered()
    project.write("docs/reference.md", "# Reference\n\nCHANGED-MARKER\n")

    site = project.build(SINGLE)

    assert rendered() == ["reference.md"]
    assert "CHANGED-MARKER" in site.pdf("reference/index.pdf").text


def test_pages_are_rendered_again_when_their_resources_change(
    project: Project, rendered
) -> None:
    project.write("docs/extra.css", "body { color: black; }")
    project.write("docs/guide/figure.svg", SVG.format(color="red"))
    project.write("docs/guide/intro.md", "# Introduction\n\n![Figure](figure.svg)\n")
    project.build(SINGLE, extra_css=["extra.css"])
    rendered()

    project.write("docs/guide/figure.svg", SVG.format(color="blue"))
    project.build(SINGLE, extra_css=["extra.css"])

    assert rendered() == ["guide/intro.md"]

    project.write("docs/extra.css", "body { color: #111; }")
    project.build(SINGLE, extra_css=["extra.css"])

    assert rendered() == sorted(PAGES)


def test_options_invalidate_the_cache(project: Project, rendered) -> None:
    project.build(SINGLE)
    rendered()

    site = project.build(
        merge(SINGLE, {"formats": {"pdf": {"header": {"center": "HEADER-MARKER"}}}})
    )

    assert rendered() == sorted(PAGES)
    assert "HEADER-MARKER" in site.pdf("reference/index.pdf").text


def test_table_of_contents_options_invalidate_the_cache(
    project: Project, rendered
) -> None:
    toc = {"enabled": True, "title": "Contents"}
    project.build(merge(SINGLE, {"formats": {"pdf": {"toc": toc}}}))
    rendered()

    site = project.build(
        merge(SINGLE, {"formats": {"pdf": {"toc": {**toc, "title": "TOC-MARKER"}}}})
    )

    assert rendered() == sorted(PAGES)
    assert "TOC-MARKER" in site.pdf("guide/advanced/index.pdf").text


def test_incomplete_documents_are_not_cached(project: Project, rendered) -> None:
    project.write("docs/reference.md", "# Reference\n\n![Missing](missing.png)\n")

    project.build(SINGLE)
    rendered()
    project.build(SINGLE)

    assert rendered() == ["reference.md"]


def test_obsolete_entries_are_pruned(project: Project) -> None:
    directory = project.path / ".cache" / "plugin" / "exporter"

    project.build(SINGLE)
    project.write("docs/reference.md", "# Reference\n\nChanged.\n")
    project.build(SINGLE)

    assert len(list(directory.glob("*.pdf"))) == len(PAGES)


def test_the_cache_can_be_disabled(project: Project, rendered) -> None:
    disabled = merge(SINGLE, {"formats": {"pdf": {"cache": {"enabled": False}}}})

    project.build(exporter=disabled)
    rendered()
    project.build(exporter=disabled)

    assert rendered() == sorted(PAGES)
    assert not (project.path / ".cache").exists()
