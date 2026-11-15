from mkdocs_exporter.core.toc import (
    TocEntry,
    TocOptions,
    heading_entries,
    render,
    subheadings,
)

HEADINGS = [
    (1, "title", "Title"),
    (2, "a", "A"),
    (3, "a1", "A.1"),
    (4, "a1x", "A.1.x"),
    (2, "b", "B"),
    (3, "b1", "B.1"),
]

PAGES = {"title": 1, "a": 2, "a1": 2, "a1x": 3, "b": 3, "b1": 4}


def test_entries_are_nested_up_to_a_level() -> None:
    entries = heading_entries(subheadings(HEADINGS), PAGES.get, depth=3)

    assert entries == [
        TocEntry("A", 2, "#a", [TocEntry("A.1", 2, "#a1")]),
        TocEntry("B", 3, "#b", [TocEntry("B.1", 4, "#b1")]),
    ]
    assert [e.title for e in heading_entries(HEADINGS[1:], PAGES.get, 2)] == ["A", "B"]


def test_headings_that_are_not_printed_are_left_out() -> None:
    pages = {**PAGES, "a": None}

    entries = heading_entries(subheadings(HEADINGS), pages.get, depth=3)

    assert [entry.title for entry in entries] == ["A.1", "B"]


def test_subheadings_leave_the_title_out() -> None:
    assert subheadings(HEADINGS) == HEADINGS[1:]
    assert subheadings(HEADINGS[1:]) == HEADINGS[1:]
    assert subheadings([]) == []


def test_rendering() -> None:
    html = render(TocOptions(title="Contents"), [TocEntry("A & B", 2, "#a")])

    assert "Contents" in html
    assert "A &amp; B" in html
    assert 'href="#a"' in html

    custom = render(
        TocOptions(
            template="{{ title }}: {% for e in entries %}{{ e.page }}{% endfor %}"
        ),
        [TocEntry("A", 2, "#a")],
    )

    assert custom == "Table of contents: 2"
