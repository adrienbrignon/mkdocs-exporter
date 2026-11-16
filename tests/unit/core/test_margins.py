import pytest

from mkdocs_exporter.core.margins import (
    ALL_BOXES,
    Margins,
    content,
    running_heads,
    sections,
    validate,
)


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
    assert Margins.of({"header": {"left": None}, "footer": {}}).stylesheet({}) == ""


def test_stylesheet_hides_headers_and_footers_on_covers() -> None:
    css = Margins.of({"footer": {"center": "{page}"}}).stylesheet({})

    assert "@bottom-center { content: counter(page);" in css
    assert (
        "@page mkdocs-exporter-cover {\n  @bottom-center { content: none; }\n}" in css
    )
    assert "@page :first" not in css


def test_stylesheet_hides_headers_and_footers_on_the_front_cover() -> None:
    css = Margins.of({"footer": {"center": "{page}"}}).stylesheet({}, front_cover=True)

    assert "@page :first {\n  @bottom-center { content: none; }\n}" in css


def test_sections_counter_style() -> None:
    css = sections(["Intro", 'A "quoted" title'])

    assert css == (
        "@counter-style mkdocs-exporter-section { system: fixed 1; "
        'symbols: "Intro" "A \\"quoted\\" title"; '
        "fallback: mkdocs-exporter-section-none; }\n"
    )


def test_running_heads_carry_the_last_heading_over() -> None:
    heads = running_heads([(1, "A"), (1, "B"), (3, "C")], range(5))

    assert heads == {0: "", 1: "A", 2: "B", 3: "C", 4: "C"}


def test_book_stylesheet_titles_named_pages() -> None:
    margins = Margins.of({"header": {"left": "{page_title}", "right": "{site_name}"}})
    css = margins.book_stylesheet(
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
    css = Margins().book_stylesheet({}, {}, [], "blank")
    blank = css.split("@page blank {")[1]

    assert blank.count("content: none !important;") == len(ALL_BOXES)
