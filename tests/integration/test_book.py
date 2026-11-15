"""End-to-end tests of aggregated documents: bookmarks, links, table of contents..."""

from __future__ import annotations

import re
from typing import Any

import pytest
from mkdocs.exceptions import Abort

from tests.conftest import Project, Site
from tests.support.pdf import OutlineItem, PdfDocument

pytestmark = pytest.mark.browser


def aggregator(**options: Any) -> dict[str, Any]:
    """Options of the main aggregator."""

    return {"formats": {"pdf": {"aggregator": options}}}


def page_of(document: PdfDocument, text: str) -> int:
    """The index of the first page containing some text."""

    pages = document.pages_containing(text)

    assert pages, f"{text!r} not found"

    return pages[0]


def titles(items: list[OutlineItem]) -> list[Any]:
    """The titles of an outline, as nested lists."""

    return [
        [item.title, titles(item.children)] if item.children else item.title
        for item in items
    ]


@pytest.fixture(scope="module")
def book(tmp_path_factory: pytest.TempPathFactory) -> Site:
    """The fixture project aggregated without covers."""

    project = Project(tmp_path_factory.mktemp("book") / "project")

    return project.build(exporter=aggregator(covers="none"))


class TestOutline:
    """Bookmarks of aggregated documents."""

    def test_follow_the_navigation(self, book: Site) -> None:
        assert titles(book.pdf("combined.pdf").outline) == [
            "Home",
            [
                "Guide",
                [
                    ["Introduction", ["Lorem"]],
                    ["Advanced", [["Deep dive", ["Sub section"]], "Another section"]],
                ],
            ],
            "Reference",
        ]

    def test_target_the_headings(self, book: Site) -> None:
        combined = book.pdf("combined.pdf")
        guide = combined.outline[1]
        advanced = guide.children[1]

        assert guide.page == page_of(combined, "Introduction")
        assert advanced.page == page_of(combined, "Deep dive")
        assert advanced.children[1].page == page_of(combined, "Another section")

    def test_depth_can_be_limited(self, project: Project) -> None:
        site = project.build(exporter=aggregator(covers="none", outline=1))

        assert titles(site.pdf("combined.pdf").outline) == [
            "Home",
            ["Guide", ["Introduction", "Advanced"]],
            "Reference",
        ]

    def test_can_be_disabled(self, project: Project) -> None:
        site = project.build(exporter=aggregator(covers="none", outline=0))

        assert site.pdf("combined.pdf").outline == []


class TestLinks:
    """Links of aggregated documents."""

    def test_links_to_aggregated_pages_are_internal(self, book: Site) -> None:
        combined = book.pdf("combined.pdf")
        home = page_of(combined, "Welcome to the")
        targets = {
            link.target_page for link in combined.internal_links if link.page == home
        }

        assert page_of(combined, "Introduction") in targets
        assert page_of(combined, "Deep dive") in targets

    def test_no_link_points_to_an_aggregated_page_on_the_website(
        self, book: Site
    ) -> None:
        links = book.pdf("combined.pdf").external_links

        assert not [
            link for link in links if link.startswith("https://example.org/docs/")
        ]

    def test_anchors_repeated_across_pages_stay_in_their_page(
        self, project: Project
    ) -> None:
        """Footnotes of every page share identifiers (`fn:1`)."""

        project.write(
            "docs/reference.md",
            "# Reference\n\nPlain reference page.[^1]\n\n[^1]: REFERENCE-NOTE\n",
        )

        site = project.build(exporter=aggregator(covers="none"))
        combined = site.pdf("combined.pdf")
        reference = page_of(combined, "Plain reference page")
        links = [link for link in combined.internal_links if link.page >= reference]

        assert links
        assert all(link.target_page is not None for link in links)
        assert all(link.target_page >= reference for link in links)  # type: ignore[operator]

    def test_links_to_other_pages_point_to_the_website(self, project: Project) -> None:
        site = project.build(exporter=aggregator(covers="none", exclude=["guide/*"]))

        assert (
            "https://example.org/docs/guide/intro/"
            in site.pdf("combined.pdf").external_links
        )


class TestTableOfContents:
    """Tables of contents of aggregated documents."""

    @pytest.fixture(scope="class")
    @classmethod
    def site(cls, tmp_path_factory: pytest.TempPathFactory) -> Site:
        project = Project(tmp_path_factory.mktemp("toc") / "project")

        return project.build(
            exporter=aggregator(covers="limits", toc={"enabled": True})
        )

    def test_follows_the_front_cover(self, site: Site) -> None:
        combined = site.pdf("combined.pdf")

        assert page_of(combined, "FRONT-COVER") == 0
        assert page_of(combined, "Table of contents") == 1

    def test_page_numbers_are_accurate(self, site: Site) -> None:
        combined = site.pdf("combined.pdf")
        toc = combined.pages_text[page_of(combined, "Table of contents")]

        for title, text in [
            ("Introduction", "Paragraph 1."),
            ("Advanced", "Back to home"),
            ("Another section", "More text."),
            ("Reference", "Plain reference page"),
        ]:
            match = re.search(rf"{title}\s*(\d+)", toc)

            assert match, f"{title} not in the table of contents"
            assert int(match.group(1)) == page_of(combined, text) + 1

    def test_entries_link_to_the_pages(self, site: Site) -> None:
        combined = site.pdf("combined.pdf")
        toc = page_of(combined, "Table of contents")
        targets = {
            link.target_page for link in combined.internal_links if link.page == toc
        }

        assert page_of(combined, "Plain reference page") in targets

    @pytest.mark.xfail(
        reason="counter(pages) of custom stylesheets is per page until combined documents are printed as a single document"
    )
    def test_page_numbers_are_consistent(self, site: Site) -> None:
        combined = site.pdf("combined.pdf")

        for index, text in enumerate(combined.pages_text):
            assert f"{index + 1} / {combined.page_count}" in text


def test_documents_can_start_on_odd_pages(project: Project) -> None:
    site = project.build(exporter=aggregator(covers="none", start="odd"))
    combined = site.pdf("combined.pdf")

    for text in ["Welcome to the", "Paragraph 1.", "Deep dive", "Plain reference page"]:
        assert page_of(combined, text) % 2 == 0, f"{text!r} isn't on an odd page"

    assert any(not text.strip() for text in combined.pages_text)


def test_several_aggregated_documents(project: Project) -> None:
    site = project.build(
        exporter={
            "formats": {
                "pdf": {
                    "aggregator": {"enabled": False},
                    "aggregators": [
                        {
                            "output": "guide.pdf",
                            "include": ["guide/*"],
                            "covers": "none",
                        },
                        {"output": "pdf/others.pdf", "exclude": ["guide/*"]},
                    ],
                }
            }
        }
    )
    guide = site.pdf("guide.pdf")
    others = site.pdf("pdf/others.pdf")

    assert "Paragraph 1." in guide.text
    assert "Deep dive" in guide.text
    assert "Welcome to the" not in guide.text
    assert "Welcome to the" in others.text
    assert "Paragraph 1." not in others.text


def test_aggregated_documents_must_have_distinct_outputs(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    with pytest.raises(Abort):
        project.build(
            exporter={"formats": {"pdf": {"aggregators": [{"output": "combined.pdf"}]}}}
        )

    assert "Several aggregators write to the same file: combined.pdf" in caplog.text
