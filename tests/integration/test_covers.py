"""End-to-end tests of cover pages."""

from __future__ import annotations

import pytest
from mkdocs.exceptions import Abort

from tests.conftest import Project

pytestmark = pytest.mark.browser

TEMPLATE = """
<style data-teleport="head">
  .cover-meta { color: #ea2027; }
</style>
<div class="cover">
  <h1>COVER {{ page.title }}</h1>
  <p class="cover-meta">SITE {{ config.site_name }}</p>
  <p>VERSION {{ VERSION }}</p>
</div>
"""


def test_covers_are_jinja_templates(project: Project) -> None:
    project.write(
        "covers/front.html", TEMPLATE.replace("{{ VERSION }}", "{{ extra.version }}")
    )

    site = project.build(extra={"version": "1.2.3"})
    text = site.pdf("guide/intro/index.pdf").text

    assert "COVER Introduction" in text
    assert "SITE Fixture" in text
    assert "VERSION 1.2.3" in text


def test_covers_are_rendered_by_the_macros_plugin(project: Project) -> None:
    """With mkdocs-macros, covers use its environment (variables, macros, filters)."""

    project.write(
        "covers/front.html", TEMPLATE.replace("{{ VERSION }}", "{{ version }}")
    )

    site = project.build(plugins=["macros"], extra={"version": "4.5.6"})

    assert "VERSION 4.5.6" in site.pdf("index.pdf").text


def test_covers_can_use_page_metadata(project: Project) -> None:
    project.write("covers/front.html", "<h1>AUTHOR {{ author }}</h1>\n")
    project.write("docs/reference.md", "---\nauthor: Ada\n---\n\n# Reference\n")

    site = project.build()

    assert "AUTHOR Ada" in site.pdf("reference/index.pdf").text


def test_covers_are_not_part_of_the_website(project: Project) -> None:
    site = project.build()

    assert "FRONT-COVER" not in site.html("index.html")
    assert "BACK-COVER" not in site.html("index.html")


def test_footnotes_come_before_the_back_cover(project: Project) -> None:
    """The back cover comes after everything else (#17)."""

    site = project.build()
    text = site.pdf("index.pdf").text

    assert text.index("This is the footnote text") < text.index("BACK-COVER")


def test_invalid_templates_fail_the_build(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    project.write("covers/front.html", "{{ page.title ")

    with pytest.raises(Abort):
        project.build()

    assert "Failed to render the cover page" in caplog.text
    assert "covers/front.html" in caplog.text


def test_teleported_styles_take_precedence_over_stylesheets(project: Project) -> None:
    css = (project.path / "pdf.css").read_text()

    project.write("pdf.css", css + "\n.cover-marker { display: block; }\n")
    project.write(
        "covers/front.html",
        '<style data-teleport="head">.cover-marker { display: none; }</style>\n'
        '<p class="cover-marker">HIDDEN-BY-COVER</p><h1>FRONT-COVER</h1>\n',
    )

    site = project.build()

    assert "HIDDEN-BY-COVER" not in site.pdf("index.pdf").text
