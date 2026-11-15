"""Tests of headers and footers."""

import pytest

from mkdocs_exporter.core.document import Layout, Position
from mkdocs_exporter.core.margins import (
    content,
    css_string,
    running_heads,
    sections,
    stylesheet,
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


def test_content_with_a_known_number_of_pages() -> None:
    assert content("{page}/{pages}", {}, pages=42) == 'counter(page) "/" "42"'


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


def test_stylesheet_sets_the_first_page_number() -> None:
    assert "counter-set: page 7;" in stylesheet({}, {}, first_page=7)
    assert "counter-set: page 7;" in stylesheet(
        {"footer": {"center": "{page}"}}, {}, first_page=7
    )


def test_sections_counter_style() -> None:
    css = sections(["Intro", 'A "quoted" title'], first_page=3)

    assert css == (
        "@counter-style mkdocs-exporter-section { system: fixed 3; "
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
