"""End-to-end tests: build the fixture project and inspect the PDF documents."""

from __future__ import annotations

import logging
import posixpath
import re

import pytest

from tests.conftest import Project, Site

pytestmark = pytest.mark.browser

PAGES = {
    "index.md": "index.pdf",
    "guide/intro.md": "guide/intro/index.pdf",
    "guide/advanced.md": "guide/advanced/index.pdf",
    "reference.md": "reference/index.pdf",
}


@pytest.fixture(scope="module", params=["material", "readthedocs"])
def site(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Site:
    """The fixture project built with the default options, for each theme."""

    project = Project(tmp_path_factory.mktemp(request.param) / "project")

    return project.build(theme={"name": request.param})


class TestPages:
    """Per-page PDF documents."""

    def test_one_document_per_page(self, site: Site) -> None:
        assert site.pdfs() == sorted([*PAGES.values(), "combined.pdf"])

    @pytest.mark.parametrize("path", PAGES.values())
    def test_documents_have_both_covers(self, site: Site, path: str) -> None:
        document = site.pdf(path)

        assert document.count("FRONT-COVER") == 1
        assert document.count("BACK-COVER") == 1
        assert document.pages_containing("FRONT-COVER") == [0]

    def test_content(self, site: Site) -> None:
        assert "Paragraph 40" in site.pdf("guide/intro/index.pdf").text
        assert "This is the footnote text" in site.pdf("index.pdf").text

    def test_all_tabs_are_printed(self, site: Site) -> None:
        assert "TAB-TWO-MARKER" in site.pdf("guide/intro/index.pdf").text

    def test_footnotes_come_before_the_back_cover(self, site: Site) -> None:
        text = site.pdf("index.pdf").text

        assert text.index("This is the footnote text") < text.index("BACK-COVER")

    def test_documents_have_bookmarks(self, site: Site) -> None:
        titles = [item.title for item in site.pdf("guide/intro/index.pdf").outline]

        assert "Introduction" in titles

    def test_links_never_target_the_local_server(self, site: Site) -> None:
        for path in site.pdfs():
            assert not any(
                "127.0.0.1" in link for link in site.pdf(path).external_links
            )

    def test_images_are_embedded(self, site: Site) -> None:
        assert site.pdf("index.pdf").image_count() >= 2

    def test_links_to_other_pages_point_to_the_website(self, site: Site) -> None:
        links = site.pdf("index.pdf").external_links

        assert "https://example.org/docs/guide/intro/" in links
        assert "https://example.org/docs/guide/advanced/#deep-dive" in links

    def test_mailto_links_are_preserved(self, site: Site) -> None:
        assert "mailto:support@example.org" in site.pdf("index.pdf").external_links

    def test_download_buttons_point_to_the_documents(self, site: Site) -> None:
        for source, pdf in PAGES.items():
            page = (
                "index.html"
                if source == "index.md"
                else posixpath.dirname(pdf) + "/index.html"
            )
            hrefs = re.findall(r'href="([^"]+\.pdf)"', site.html(page))

            assert hrefs, f"no download button in {page}"
            for href in hrefs:
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(page), href)
                )

                assert target == pdf


class TestAggregator:
    """The combined PDF document."""

    def test_contains_every_page(self, site: Site) -> None:
        combined = site.pdf("combined.pdf")
        pages = sum(site.pdf(path).page_count for path in PAGES.values())

        assert combined.page_count == pages
        assert combined.count("FRONT-COVER") == len(PAGES)
        assert "Paragraph 40" in combined.text

    def test_page_numbers_are_continuous(self, site: Site) -> None:
        combined = site.pdf("combined.pdf")
        total = combined.page_count

        for index, text in enumerate(combined.pages_text):
            assert f"{index + 1} / {total}" in text


@pytest.mark.parametrize(
    ("covers", "front", "back"),
    [
        ("all", 4, 4),
        ("none", 0, 0),
        ("limits", 1, 1),
        ("book", 4, 1),
        ("front", 4, 0),
        ("back", 0, 4),
    ],
)
def test_aggregator_cover_modes(
    project: Project, covers: str, front: int, back: int
) -> None:
    site = project.build(
        exporter={"formats": {"pdf": {"aggregator": {"covers": covers}}}}
    )
    combined = site.pdf("combined.pdf")

    assert combined.count("FRONT-COVER") == front
    assert combined.count("BACK-COVER") == back


def test_page_numbers_are_continuous_without_covers(project: Project) -> None:
    site = project.build(
        exporter={"formats": {"pdf": {"aggregator": {"covers": "limits"}}}}
    )
    combined = site.pdf("combined.pdf")

    for index, text in enumerate(combined.pages_text):
        assert f"{index + 1} / {combined.page_count}" in text


def test_aggregator_metadata(project: Project) -> None:
    site = project.build(
        exporter={
            "formats": {"pdf": {"aggregator": {"metadata": {"/Title": "Handbook"}}}}
        }
    )

    assert site.pdf("combined.pdf").metadata.get("/Title") == "Handbook"


def test_explicit_mode_only_renders_opted_in_pages(project: Project) -> None:
    project.write("docs/reference.md", "---\npdf: true\n---\n\n# Reference\n")

    site = project.build(exporter={"formats": {"pdf": {"explicit": True}}})

    assert site.pdfs() == ["combined.pdf", "reference/index.pdf"]


def test_pages_can_opt_out(project: Project) -> None:
    project.write("docs/reference.md", "---\npdf: false\n---\n\n# Reference\n")

    site = project.build()

    assert "reference/index.pdf" not in site.pdfs()
    assert "Plain reference page" not in site.pdf("combined.pdf").text


def test_pages_can_hide_covers(project: Project) -> None:
    project.write("docs/reference.md", "---\nhide:\n  - covers\n---\n\n# Reference\n")

    site = project.build()
    document = site.pdf("reference/index.pdf")

    assert document.count("FRONT-COVER") == 0
    assert document.count("BACK-COVER") == 0


def test_pdf_generation_can_be_disabled(project: Project) -> None:
    site = project.build(exporter={"formats": {"pdf": {"enabled": False}}})

    assert site.pdfs() == []


@pytest.fixture(scope="module")
def flat_site(tmp_path_factory: pytest.TempPathFactory) -> Site:
    """The fixture project built with `use_directory_urls: false`."""

    project = Project(tmp_path_factory.mktemp("flat") / "project")

    return project.build(use_directory_urls=False)


class TestDirectoryUrlsDisabled:
    """Sites built with `use_directory_urls: false`."""

    def test_one_document_per_page(self, flat_site: Site) -> None:
        assert flat_site.pdfs() == [
            "combined.pdf",
            "guide/advanced.pdf",
            "guide/intro.pdf",
            "index.pdf",
            "reference.pdf",
        ]

    def test_download_buttons_point_to_the_documents(self, flat_site: Site) -> None:
        html = flat_site.html("guide/intro.html")

        assert 'href="intro.pdf"' in html


@pytest.mark.parametrize("use_directory_urls", [True, False])
def test_no_browser_errors(
    project: Project, exporter_logs, use_directory_urls: bool
) -> None:
    project.build(use_directory_urls=use_directory_urls)

    assert exporter_logs(logging.WARNING) == []


def test_excluded_stylesheets(project: Project) -> None:
    project.write("docs/drafts/excluded.css", "body { color: red; }")

    site = project.build(exclude_docs="drafts/")

    assert "combined.pdf" in site.pdfs()


def test_unsupported_themes_fall_back_to_a_generic_theme(project: Project) -> None:
    site = project.build(theme={"name": "mkdocs"})

    assert "index.pdf" in site.pdfs()


def test_removed_covers_on_their_own_page_are_not_counted(project: Project) -> None:
    """Hidden content next to a cover doesn't make its page count as content."""

    css = (project.path / "pdf.css").read_text()

    project.write("pdf.css", css + "\n.back-cover { break-before: page; }\n")
    project.write(
        "scripts/hidden.js",
        "document.querySelector('article, [role=\"main\"], body')"
        ".insertAdjacentHTML('beforeend', '<p style=\"display: none\">HIDDEN</p>');\n",
    )

    site = project.build(
        exporter={
            "formats": {
                "pdf": {
                    "scripts": ["scripts/hidden.js"],
                    "aggregator": {"covers": "front"},
                }
            }
        }
    )
    combined = site.pdf("combined.pdf")
    pages = sum(site.pdf(path).page_count for path in PAGES.values())

    assert combined.page_count == pages - len(PAGES)
    assert f"{combined.page_count} / {combined.page_count}" in combined.pages_text[-1]
