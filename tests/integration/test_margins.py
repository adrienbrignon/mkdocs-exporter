"""End-to-end tests of headers and footers."""

from __future__ import annotations

import pytest

from tests.conftest import Project, Site

pytestmark = pytest.mark.browser

MARGINS = {
    "header": {"left": "{site_name}", "right": "TITLE {page_title}"},
    "footer": {"left": "SECTION {section}", "right": "PAGE {page} OF {pages}"},
}


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Site:
    project = Project(tmp_path_factory.mktemp("margins") / "project")

    return project.build(exporter={"formats": {"pdf": MARGINS}})


def test_headers_and_footers(site: Site) -> None:
    document = site.pdf("guide/intro/index.pdf")
    page = document.pages_text[1]

    assert "Fixture" in page
    assert "TITLE Introduction" in page
    assert f"PAGE 2 OF {document.page_count}" in page


def test_sections_are_running_headings(site: Site) -> None:
    document = site.pdf("guide/advanced/index.pdf")
    text = "\n".join(document.pages_text[1:])

    assert "SECTION Advanced" in text
    assert "¶" not in text


def test_covers_have_no_header_nor_footer(site: Site) -> None:
    document = site.pdf("index.pdf")

    for index in document.pages_containing("FRONT-COVER") + document.pages_containing(
        "BACK-COVER"
    ):
        assert "PAGE " not in document.pages_text[index]
        assert "TITLE " not in document.pages_text[index]


def test_aggregated_documents_are_numbered_continuously(site: Site) -> None:
    combined = site.pdf("combined.pdf")
    numbered = [i for i, text in enumerate(combined.pages_text) if "PAGE " in text]

    assert numbered
    for index in numbered:
        assert (
            f"PAGE {index + 1} OF {combined.page_count}" in combined.pages_text[index]
        )


def test_page_titles_follow_aggregated_documents(project: Project) -> None:
    site = project.build(
        exporter={"formats": {"pdf": {**MARGINS, "aggregator": {"covers": "none"}}}}
    )
    combined = site.pdf("combined.pdf")
    reference = combined.pages_containing("Plain reference page")[0]

    assert "TITLE Reference" in combined.pages_text[reference]
