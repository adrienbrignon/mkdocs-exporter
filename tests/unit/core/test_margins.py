"""Tests of headers and footers."""

import pytest

from mkdocs_exporter.core.margins import content, css_string, stylesheet, validate


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
    assert content("{section}", values) == 'var(--mkdocs-exporter-section, "")'
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

    assert "@bottom-center { content: counter(page); white-space: pre; }" in css
    assert (
        "@page mkdocs-exporter-cover {\n  @bottom-center { content: none; }\n}" in css
    )
    assert "@page :first" not in css


def test_stylesheet_hides_headers_and_footers_on_the_front_cover() -> None:
    css = stylesheet({"footer": {"center": "{page}"}}, {}, front_cover=True)

    assert "@page :first {\n  @bottom-center { content: none; }\n}" in css
