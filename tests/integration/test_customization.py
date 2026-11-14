"""End-to-end tests of the customization points offered to users."""

from __future__ import annotations

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


@pytest.mark.xfail(
    reason="scripts are tagged with an undefined variable (path=stylesheet)"
)
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


def test_elements_can_be_teleported(project: Project) -> None:
    project.write(
        "docs/reference.md",
        '# Reference\n\n<div id="target"></div>\n\nPlain reference page.\n\n'
        '<span data-teleport="#target">TELEPORT-MARKER</span>\n',
    )

    site = project.build()
    text = site.pdf("reference/index.pdf").text

    assert text.index("TELEPORT-MARKER") < text.index("Plain reference page")
    assert 'id="target"><span>TELEPORT-MARKER</span>' in site.html(
        "reference/index.html"
    )


def test_pages_can_override_covers(project: Project) -> None:
    project.write("covers/special.html", "<div><h1>SPECIAL-COVER</h1></div>\n")
    project.write(
        "docs/reference.md",
        "---\ncovers:\n  front: covers/special.html\n---\n\n# Reference\n",
    )

    site = project.build()
    document = site.pdf("reference/index.pdf")

    assert document.count("SPECIAL-COVER") == 1
    assert document.count("FRONT-COVER") == 0
    assert document.count("BACK-COVER") == 1


@pytest.mark.xfail(
    reason="the path of site_url is kept when rewriting links with 'url'"
)
def test_links_can_target_another_url(project: Project) -> None:
    site = project.build(
        exporter={"formats": {"pdf": {"url": "https://docs.example.com/"}}}
    )

    assert (
        "https://docs.example.com/guide/intro/" in site.pdf("index.pdf").external_links
    )


@pytest.mark.xfail(reason="links resolve to temporary file:// locations")
def test_links_without_site_url_are_relative(project: Project) -> None:
    site = project.build(site_url="")
    links = site.pdf("index.pdf").external_links

    assert "guide/intro/" in links
    assert not any(link.startswith(("file:", "http://127.")) for link in links)
