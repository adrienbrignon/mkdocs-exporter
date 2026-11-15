"""Tests of headers and footers."""

import pytest

from mkdocs_exporter.core.document import Layout, Position
from mkdocs_exporter.core.margins import (
    ALL_BOXES,
    book_stylesheet,
    content,
    css_string,
    running_heads,
    sections,
    stylesheet,
    top_margin,
    validate,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("plain", '"plain"'),
        ('a "quoted" word', '"a \\"quoted\\" word"'),
        ("back\\slash", '"back\\\\slash"'),
        ("two\nlines", '"two\\A lines"'),
    ],
)
def test_css_string(text: str, expected: str) -> None:
    assert css_string(text) == expected


def test_content_with_placeholders() -> None:
    values = {"site_name": "Docs", "page_title": "Intro"}

    assert content("{site_name}: {page_title}", values) == '"Docs" ": " "Intro"'
    assert content("{page}/{pages}", values) == 'counter(page) "/" counter(pages)'
    assert content("{section}", values) == "counter(page, mkdocs-exporter-section)"
    assert content("", values) == '""'


@pytest.mark.parametrize("text", ["{unknown}", "{page_number}", "{}", "Page {PAGE}"])
def test_unknown_placeholders_are_rejected(text: str) -> None:
    with pytest.raises(ValueError, match="unknown placeholder"):
        validate(text)


def test_values_cannot_inject_css() -> None:
    css = content("{page_title}", {"page_title": '"; } body { color: red; } x { "'})

    assert css.count('"') - css.count('\\"') == 2


def test_stylesheet_is_empty_without_headers_and_footers() -> None:
    assert stylesheet({"header": {"left": None}, "footer": {}}, {}) == ""


def test_stylesheet_hides_headers_and_footers_on_covers() -> None:
    css = stylesheet({"footer": {"center": "{page}"}}, {})

    assert "@bottom-center { content: counter(page);" in css
    assert (
        "@page mkdocs-exporter-cover {\n  @bottom-center { content: none; }\n}" in css
    )
    assert "@page :first" not in css


def test_stylesheet_hides_headers_and_footers_on_the_front_cover() -> None:
    css = stylesheet({"footer": {"center": "{page}"}}, {}, front_cover=True)

    assert "@page :first {\n  @bottom-center { content: none; }\n}" in css


def test_sections_counter_style() -> None:
    css = sections(["Intro", 'A "quoted" title'])

    assert css == (
        "@counter-style mkdocs-exporter-section { system: fixed 1; "
        'symbols: "Intro" "A \\"quoted\\" title"; '
        "fallback: mkdocs-exporter-section-none; }\n"
    )


def test_running_heads_carry_the_last_heading_over() -> None:
    layout = Layout(
        pages=5,
        anchors={"a": Position(page=1), "b": Position(page=1), "c": Position(page=3)},
    )

    titles = running_heads([("a", "A"), ("b", "B"), ("c", "C"), ("x", "X")], layout)

    assert titles == ["", "A", "B", "C", "C"]


def test_book_stylesheet_titles_named_pages() -> None:
    css = book_stylesheet(
        {"header": {"left": "{page_title}", "right": "{site_name}"}},
        {"site_name": "Site"},
        {"mkdocs-exporter-part-1": "Intro"},
        ["mkdocs-exporter-front-cover"],
        "mkdocs-exporter-blank",
    )

    assert '@top-left { content: ""; ' in css
    assert '@page mkdocs-exporter-part-1 {\n  @top-left { content: "Intro"; ' in css
    assert (
        "@top-right" not in css.split("@page mkdocs-exporter-part-1")[1].split("}")[0]
    )
    assert "@page mkdocs-exporter-front-cover {\n  @top-left { content: none; }" in css


def test_book_stylesheet_empties_every_box_of_blank_pages() -> None:
    css = book_stylesheet({}, {}, {}, [], "blank")
    blank = css.split("@page blank {")[1]

    assert blank.count("content: none !important;") == len(ALL_BOXES)


@pytest.mark.parametrize(
    ("name", "first", "right", "expected"),
    [
        (None, False, True, 20.0),
        (None, True, True, 0.0),
        ("cover", False, True, 10.0),
        ("cover", True, True, 10.0),
        (None, False, False, 30.0),
    ],
)
def test_top_margin_follows_page_selectors(
    name: str | None, first: bool, right: bool, expected: float
) -> None:
    rules = [
        {"selector": "", "marginTop": "20px"},
        {"selector": ":first", "marginTop": "0"},
        {"selector": "cover", "marginTop": "10px"},
        {"selector": ":left", "marginTop": "30px"},
        {"selector": "other", "marginTop": "auto"},
    ]

    assert top_margin(rules, name, first=first, right=right) == expected


def test_top_margin_converts_lengths() -> None:
    assert top_margin([{"selector": "", "marginTop": "1in"}], None, False, True) == 96
    assert top_margin([{"selector": "", "marginTop": "2em"}], None, False, True) == 0
