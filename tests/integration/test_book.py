from __future__ import annotations

import re
from typing import Any

import pytest
from mkdocs.exceptions import Abort

from mkdocs_exporter.core.books import printer
from mkdocs_exporter.core.books.assembly import reuse
from tests.conftest import BOOK_BUTTON, Project, Site, single_book
from tests.support.pdf import OutlineItem, PdfDocument

pytestmark = pytest.mark.browser


def with_book(**options: Any) -> dict[str, Any]:
    """Options of the plugin with a single book (`combined.pdf`)."""

    return {"formats": {"pdf": single_book(**options)}}


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
    """The fixture project combined into a book without covers."""

    project = Project(tmp_path_factory.mktemp("book") / "project")

    return project.build(exporter=with_book(covers="none"))


class TestOutline:
    """Bookmarks of books."""

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
        site = project.build(exporter=with_book(covers="none", outline=1))

        assert titles(site.pdf("combined.pdf").outline) == [
            "Home",
            ["Guide", ["Introduction", "Advanced"]],
            "Reference",
        ]

    def test_can_be_disabled(self, project: Project) -> None:
        site = project.build(exporter=with_book(covers="none", outline=0))

        assert site.pdf("combined.pdf").outline == []


class TestLinks:
    """Links of books."""

    def test_links_to_pages_of_the_book_are_internal(self, book: Site) -> None:
        combined = book.pdf("combined.pdf")
        home = page_of(combined, "Welcome to the")
        targets = {
            link.target_page for link in combined.internal_links if link.page == home
        }

        assert page_of(combined, "Introduction") in targets
        assert page_of(combined, "Deep dive") in targets

    def test_no_link_points_to_a_page_of_the_book_on_the_website(
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

        site = project.build(exporter=with_book(covers="none"))
        combined = site.pdf("combined.pdf")
        reference = page_of(combined, "Plain reference page")
        links = [link for link in combined.internal_links if link.page >= reference]

        assert links
        assert all(link.target_page is not None for link in links)
        assert all(link.target_page >= reference for link in links)  # type: ignore[operator]

    def test_links_to_other_pages_point_to_the_website(self, project: Project) -> None:
        site = project.build(exporter=with_book(covers="none", exclude=["guide/*"]))

        assert (
            "https://example.org/docs/guide/intro/"
            in site.pdf("combined.pdf").external_links
        )


class TestTableOfContents:
    """Tables of contents of books."""

    @pytest.fixture(scope="class")
    @classmethod
    def site(cls, tmp_path_factory: pytest.TempPathFactory) -> Site:
        project = Project(tmp_path_factory.mktemp("toc") / "project")

        return project.build(exporter=with_book(covers="limits", toc={"enabled": True}))

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

    def test_page_numbers_are_consistent(self, site: Site) -> None:
        combined = site.pdf("combined.pdf")

        for index, text in enumerate(combined.pages_text):
            assert f"{index + 1} / {combined.page_count}" in text


def test_documents_can_start_on_odd_pages(project: Project) -> None:
    site = project.build(exporter=with_book(covers="none", start="odd"))
    combined = site.pdf("combined.pdf")

    for text in ["Welcome to the", "Paragraph 1.", "Deep dive", "Plain reference page"]:
        assert page_of(combined, text) % 2 == 0, f"{text!r} isn't on an odd page"

    assert any(not text.strip() for text in combined.pages_text)


def test_several_books(project: Project) -> None:
    site = project.build(
        exporter={
            "formats": {
                "pdf": {
                    "books": [
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


def test_book_buttons_link_to_the_first_book_of_the_page(project: Project) -> None:
    site = project.build(
        exporter={
            "formats": {
                "pdf": {
                    "books": [
                        {
                            "output": "guide.pdf",
                            "include": ["guide/*"],
                            "covers": "none",
                            "metadata": {"title": "The guide"},
                        },
                        {"output": "pdf/all.pdf", "covers": "none"},
                    ],
                }
            },
            "buttons": [BOOK_BUTTON],
        }
    )
    guide = site.html("guide/intro/index.html")
    home = site.html("index.html")

    assert 'href="../../guide.pdf"' in guide
    assert 'download="The guide.pdf"' in guide
    assert 'href="pdf/all.pdf"' in home
    assert site.pdfs().count("guide.pdf") == 1


def test_books_reuse_the_content_prepared_for_pages(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pages are parsed once for their document and books (but the first page, the
    book's shell); the content of a page is reused by a single book."""

    reused: list[str] = []

    def spy(index: int, document: Any, *args: Any) -> Any:
        reused.append(document.id)

        return reuse(index, document, *args)

    monkeypatch.setattr(printer, "reuse", spy)
    project.build(
        exporter={
            "formats": {
                "pdf": {
                    "books": [
                        {"output": "all.pdf", "covers": "none"},
                        {"output": "guide.pdf", "include": ["guide/*"]},
                    ]
                }
            }
        }
    )

    assert reused == ["guide/intro.md", "guide/advanced.md", "reference.md"]


@pytest.mark.parametrize("tagged", [None, False], ids=["default", "disabled"])
def test_books_are_tagged(project: Project, tagged: bool | None) -> None:
    options = {} if tagged is None else {"tagged": tagged}
    site = project.build(exporter=with_book(covers="none", **options))
    book = site.pdf("combined.pdf")

    assert book.tagged is (tagged is None)
    assert book.outline
    assert site.pdf("index.pdf").tagged


def test_books_must_have_distinct_outputs(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    with pytest.raises(Abort):
        project.build(
            exporter={
                "formats": {
                    "pdf": {
                        "books": [
                            {"output": "combined.pdf"},
                            {"output": "/combined.pdf"},
                        ]
                    }
                }
            }
        )

    assert "Several books are written to the same file: combined.pdf" in caplog.text


def test_the_deprecated_aggregator_is_a_book(
    project: Project, caplog: pytest.LogCaptureFixture
) -> None:
    site = project.build(
        exporter={
            "formats": {
                "pdf": {"books": [], "aggregator": {"enabled": True, "covers": "none"}}
            }
        }
    )

    assert "Paragraph 1." in site.pdf("combined.pdf").text
    assert "'formats.pdf.aggregator' is deprecated" in caplog.text


def test_bookmarks_show_their_heading(book: Site) -> None:
    """Destinations are lowered by the page's top margin (Chromium leaves it out)."""

    combined = book.pdf("combined.pdf")
    advanced = combined.outline[1].children[1]

    for item in [advanced, *advanced.children]:
        assert item.page is not None
        assert item.top is not None

        position = combined.baseline(item.title, item.page)

        assert position is not None, item.title

        baseline, size = position

        assert 0 < item.top - baseline < 2 * size, item.title


def test_documents_with_covers_can_start_on_odd_pages(project: Project) -> None:
    site = project.build(
        exporter=with_book(covers="front", start="odd", toc={"enabled": True})
    )
    combined = site.pdf("combined.pdf")
    covers = combined.pages_containing("FRONT-COVER")
    blanks = [i for i, text in enumerate(combined.pages_text) if not text.strip()]

    assert len(covers) == 4
    assert all(page % 2 == 0 for page in covers)
    assert blanks == [covers[1] - 1]


@pytest.mark.parametrize("covers", ["all", "none", "limits", "book", "front", "back"])
def test_pages_are_numbered_across_documents(project: Project, covers: str) -> None:
    combined = project.build(exporter=with_book(covers=covers)).pdf("combined.pdf")

    for index, text in enumerate(combined.pages_text):
        assert f"{index + 1} / {combined.page_count}" in text


@pytest.mark.parametrize("theme", ["material", "readthedocs"])
def test_every_table_of_contents_entry_leads_to_its_page(
    project: Project, theme: str
) -> None:
    site = project.build(
        exporter=with_book(covers="all", toc={"enabled": True}),
        theme={"name": theme},
    )
    combined = site.pdf("combined.pdf")
    toc = combined.pages_text[page_of(combined, "Table of contents")]
    entries = re.findall(r"^(\w[\w ]*?)\s*(\d+)$", toc, re.MULTILINE)

    assert len(entries) >= 8

    for title, number in entries:
        if title != "Guide":  # A section of the navigation.
            assert title in combined.pages_text[int(number) - 1], title


def test_no_link_points_to_the_local_server(project: Project) -> None:
    """Links created by scripts are resolved against the website, not the server."""

    project.write(
        "scripts/link.js",
        "const link = document.createElement('a');\n"
        "link.href = '/docs/reference/';\n"
        "link.textContent = 'SCRIPTED-LINK';\n"
        "document.querySelector('article').appendChild(link);\n",
    )

    site = project.build(
        exporter={"formats": {"pdf": {"scripts": ["scripts/link.js"]}}}
    )
    combined = site.pdf("combined.pdf")

    assert "https://example.org/docs/reference/" in combined.external_links
    assert not [link for link in combined.external_links if "127.0.0.1" in link]


def test_links_without_site_url_are_relative_to_the_document(project: Project) -> None:
    site = project.build(
        exporter=with_book(output="pdf/book.pdf", covers="none", exclude=["guide/*"]),
        site_url="",
    )
    links = site.pdf("pdf/book.pdf").external_links

    assert "../guide/intro/" in links
    assert not any(link.startswith(("file:", "http://127.")) for link in links)


def test_tabs_of_several_pages_keep_their_content(project: Project) -> None:
    """Radio groups of tabs are namespaced: a tab set doesn't uncheck another's."""

    project.write(
        "docs/reference.md",
        '# Reference\n\n=== "One"\n\n    REFERENCE-TAB-ONE\n\n'
        '=== "Two"\n\n    REFERENCE-TAB-TWO\n',
    )
    project.write(
        "scripts/checked.js",
        "const checked = document.querySelectorAll('input[type=radio]:checked');\n"
        "document.querySelector('article').insertAdjacentHTML(\n"
        "  'beforeend', `<p>CHECKED=${checked.length}</p>`);\n",
    )

    site = project.build(
        exporter={
            "formats": {
                "pdf": {
                    "scripts": ["scripts/checked.js"],
                    **single_book(covers="none"),
                }
            }
        }
    )
    combined = site.pdf("combined.pdf")

    assert "CHECKED=2" in combined.text

    for marker in [
        "Content of the first tab.",
        "TAB-TWO-MARKER",
        "REFERENCE-TAB-ONE",
        "REFERENCE-TAB-TWO",
    ]:
        assert combined.count(marker) == 1, marker


def test_cover_styles_depending_on_the_page_stay_in_their_part(
    project: Project,
) -> None:
    project.write(
        "covers/front.html",
        '<style data-mkdocs-exporter-teleport="head">'
        '.cover-title::after { content: " ({{ page.title }})"; }</style>\n'
        '<div class="front-cover"><h1 class="cover-title">FRONT-COVER</h1></div>\n',
    )

    combined = project.build(exporter=with_book(covers="front")).pdf("combined.pdf")
    covers = combined.pages_containing("FRONT-COVER")

    assert [
        re.search(r"FRONT-COVER \((.*)\)", combined.pages_text[page]).group(1)  # type: ignore[union-attr]
        for page in covers
    ] == ["Home", "Introduction", "Advanced", "Reference"]


def test_first_page_rules_apply_to_every_front_cover(project: Project) -> None:
    project.write("first.css", "@page :first { @bottom-center { content: none; } }")

    site = project.build(
        exporter={
            "formats": {
                "pdf": {
                    "stylesheets": ["pdf.css", "first.css"],
                    **single_book(covers="front"),
                }
            }
        }
    )
    combined = site.pdf("combined.pdf")

    for page in combined.pages_containing("FRONT-COVER"):
        assert " / " not in combined.pages_text[page]

    assert f"2 / {combined.page_count}" in combined.pages_text[1]


def test_wide_content_does_not_shrink_other_documents(project: Project) -> None:
    project.write(
        "docs/reference.md", '# Reference\n\n<div style="width: 3000px">Wide.</div>\n'
    )

    site = project.build(exporter=with_book(covers="none"))

    assert site.pdf("combined.pdf").font_size("Introduction") == site.pdf(
        "guide/intro/index.pdf"
    ).font_size("Introduction")


def test_headings_that_are_not_printed_are_left_out(project: Project) -> None:
    project.write(
        "docs/reference.md",
        "# Reference\n\nPlain reference page.\n\n"
        "## HIDDEN-HEADING { .mkdocs-exporter-ignore }\n\n## Shown heading\n",
    )

    site = project.build(exporter=with_book(covers="none", toc={"enabled": True}))
    combined = site.pdf("combined.pdf")
    toc = combined.pages_text[page_of(combined, "Table of contents")]

    assert "HIDDEN-HEADING" not in combined.text
    assert "Shown heading" in toc
    assert "HIDDEN-HEADING" not in str(titles(combined.outline))


BARE_THEME = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{{ page.title }}</title></head>
<body>
<div>{{ page.content }}</div>
<script>document.body.insertAdjacentHTML("beforeend", "<p>SCRIPT-RAN</p>")</script>
</body>
</html>
"""
"""A theme without content element: pages are their whole body."""


def test_themes_without_content_element(project: Project) -> None:
    """Every page's body makes a part of its own, whose scripts run once."""

    project.write("theme/main.html", BARE_THEME)

    site = project.build(
        exporter=with_book(covers="none", start="odd"),
        theme={"name": None, "custom_dir": "theme"},
    )
    combined = site.pdf("combined.pdf")

    for text in ["Welcome to the", "Paragraph 1.", "Deep dive", "Plain reference page"]:
        assert page_of(combined, text) % 2 == 0, f"{text!r} isn't on an odd page"

    assert sum(text.count("SCRIPT-RAN") for text in combined.pages_text) == 1
