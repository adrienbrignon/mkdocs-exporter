from __future__ import annotations

import logging

import pytest

from tests.conftest import Project

pytestmark = pytest.mark.browser

SCRIPT = """
document.querySelector('article, [role="main"], body')
  .insertAdjacentHTML('beforeend', '<p>SCRIPT-MARKER</p>');
"""

RENDER_HOOK = """
window.MkDocsExporter = {
  render: async () => {
    await new Promise((resolve) => setTimeout(resolve, 300));
    document.querySelector('article, [role="main"], body')
      .insertAdjacentHTML('beforeend', '<p>HOOK-MARKER</p>');
  },
};
"""


def test_custom_scripts_are_executed(project: Project) -> None:
    project.write("scripts/extra.js", SCRIPT)

    site = project.build(
        exporter={"formats": {"pdf": {"scripts": ["scripts/extra.js"]}}}
    )

    assert "SCRIPT-MARKER" in site.pdf("index.pdf").text


def test_custom_scripts_without_stylesheets(project: Project) -> None:
    project.write("scripts/extra.js", SCRIPT)

    site = project.build(
        exporter={
            "formats": {"pdf": {"stylesheets": [], "scripts": ["scripts/extra.js"]}}
        }
    )

    assert "SCRIPT-MARKER" in site.pdf("index.pdf").text


def test_render_hook_is_awaited_before_pagination(project: Project) -> None:
    project.write("scripts/hook.js", RENDER_HOOK)

    site = project.build(
        exporter={"formats": {"pdf": {"scripts": ["scripts/hook.js"]}}}
    )

    assert "HOOK-MARKER" in site.pdf("index.pdf").text


@pytest.mark.parametrize(
    "attribute",
    ["data-mkdocs-exporter-teleport", "data-teleport"],
    ids=["exporter", "deprecated"],
)
def test_elements_can_be_teleported(
    project: Project, attribute: str, caplog: pytest.LogCaptureFixture
) -> None:
    project.write(
        "docs/reference.md",
        '# Reference\n\n<div id="target"></div>\n\nPlain reference page.\n\n'
        f'<span {attribute}="#target">TELEPORT-MARKER</span>\n',
    )
    project.write(
        "covers/front.html",
        f'<style {attribute}="head">.cover-marker {{ color: red; }}</style>\n'
        "<div><h1>FRONT-COVER</h1></div>\n",
    )

    site = project.build()
    text = site.pdf("reference/index.pdf").text
    deprecated = caplog.text.count("'data-teleport' attribute is deprecated")

    assert text.index("TELEPORT-MARKER") < text.index("Plain reference page")
    assert 'id="target"><span>TELEPORT-MARKER</span>' in site.html(
        "reference/index.html"
    )
    assert deprecated == (attribute == "data-teleport")


@pytest.mark.parametrize(
    "front_matter",
    [
        "covers:\n  front: covers/special.html",
        "exporter:\n  pdf:\n    covers:\n      front: covers/special.html",
    ],
    ids=["deprecated", "exporter"],
)
def test_pages_can_override_covers(project: Project, front_matter: str) -> None:
    project.write("covers/special.html", "<div><h1>SPECIAL-COVER</h1></div>\n")
    project.write("docs/reference.md", f"---\n{front_matter}\n---\n\n# Reference\n")

    site = project.build()
    document = site.pdf("reference/index.pdf")

    assert document.count("SPECIAL-COVER") == 1
    assert document.count("FRONT-COVER") == 0
    assert document.count("BACK-COVER") == 1


def test_links_can_target_another_url(project: Project) -> None:
    site = project.build(
        exporter={"formats": {"pdf": {"url": "https://docs.example.com/"}}}
    )

    assert (
        "https://docs.example.com/guide/intro/" in site.pdf("index.pdf").external_links
    )


def test_links_without_site_url_are_relative(project: Project) -> None:
    site = project.build(site_url="")
    links = site.pdf("index.pdf").external_links

    assert "guide/intro/" in links
    assert not any(link.startswith(("file:", "http://127.")) for link in links)


def test_shadow_trees_are_printed(project: Project) -> None:
    """Content rendered in (closed) shadow trees, like Material's diagrams, is printed."""

    project.write(
        "scripts/shadow.js",
        "const host = document.createElement('div');\n"
        "host.attachShadow({ mode: 'closed' }).innerHTML = '<p>SHADOW-MARKER</p>';\n"
        "document.querySelector('article, [role=\"main\"], body').appendChild(host);\n",
    )

    site = project.build(
        exporter={"formats": {"pdf": {"scripts": ["scripts/shadow.js"]}}}
    )

    assert "SHADOW-MARKER" in site.pdf("index.pdf").text


def test_elements_can_be_ignored(project: Project) -> None:
    """Elements with the `mkdocs-exporter-ignore` class aren't printed (#33)."""

    project.write(
        "docs/reference.md",
        "# Reference\n\nPlain reference page.\n\n"
        '<p class="mkdocs-exporter-ignore">IGNORED-MARKER</p>\n',
    )

    site = project.build()

    assert "IGNORED-MARKER" not in site.pdf("reference/index.pdf").text
    assert "IGNORED-MARKER" in site.html("reference/index.html")


def test_elements_can_be_left_out_of_the_website(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    """Elements of the `mkdocs-exporter-only` class (or with the deprecated
    `data-decompose="true"` attribute) are only in documents."""

    project.write(
        "docs/reference.md",
        "# Reference\n\nPlain reference page.\n\n"
        '<p class="mkdocs-exporter-only">ONLY-MARKER</p>\n'
        '<p data-decompose="true">DECOMPOSED-MARKER</p>\n',
    )

    site = project.build()
    html = site.html("reference/index.html")
    text = site.pdf("reference/index.pdf").text

    assert "ONLY-MARKER" not in html
    assert "DECOMPOSED-MARKER" not in html
    assert "ONLY-MARKER" in text
    assert "DECOMPOSED-MARKER" in text
    assert caplog.text.count("'data-decompose=\"true\"' is deprecated") == 1


def test_titles_can_be_inserted(project: Project) -> None:
    """Pages without a first-level heading get their title (#53)."""

    project.write(
        "docs/reference.md", "---\ntitle: The reference\n---\n\nNo heading here.\n"
    )

    site = project.build(
        theme={"name": "readthedocs"}, exporter={"formats": {"pdf": {"title": True}}}
    )
    text = site.pdf("reference/index.pdf").text

    assert text.index("The reference") < text.index("No heading here.")


def test_material_search_is_not_loaded(project: Project, exporter_logs) -> None:
    """Material's search index isn't loaded by every document."""

    pytest.importorskip("material")
    project.write(
        "scripts/search.js",
        "window.MkDocsExporter = { after: () => document.querySelector('article')"
        ".insertAdjacentHTML('beforeend', document.querySelector("
        "'[data-md-component=search]') ? '<p>SEARCH-PRESENT</p>' : '') };",
    )

    site = project.build(
        exporter={"formats": {"pdf": {"scripts": ["scripts/search.js"]}}},
        plugins=["search"],
    )

    assert "SEARCH-PRESENT" not in site.pdf("index.pdf").text
    assert 'data-md-component="search"' in site.html("index.html")
    assert exporter_logs(logging.WARNING) == []
