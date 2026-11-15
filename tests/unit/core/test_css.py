import pytest

from mkdocs_exporter.core.css import (
    PageMargin,
    PageRule,
    PageSelector,
    pixels,
    rename_pages,
    rename_selector_ids,
    rewrite_ids,
    rewrite_urls,
    scope,
    selector_list,
    split_page_rules,
    string,
    top_margin,
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
def test_string(text: str, expected: str) -> None:
    assert string(text) == expected


@pytest.mark.parametrize(
    ("length", "expected"),
    [("1in", 96.0), ("10PX", 10.0), ("0", 0.0), ("2em", None), ("auto", None)],
)
def test_pixels(length: str, expected: float | None) -> None:
    assert pixels(length) == expected


def test_page_selectors() -> None:
    assert selector_list(":first, cover:left ,x") == [":first", "cover:left", "x"]
    assert PageSelector.parse(":first") == PageSelector(None, ("first",))
    assert PageSelector.parse("cover:LEFT") == PageSelector("cover", ("left",))
    assert PageSelector.parse("") == PageSelector()
    assert PageSelector.parse("two names") is None
    assert PageSelector.parse(":") is None


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
        PageMargin("", "20px"),
        PageMargin(":first", "0"),
        PageMargin("cover", "10px"),
        PageMargin(":left", "30px"),
        PageMargin("other", "auto"),
    ]

    assert top_margin(rules, name, first=first, right=right) == expected


def test_top_margin_converts_lengths() -> None:
    assert top_margin([PageMargin("", "1in")], None, False, True) == 96
    assert top_margin([PageMargin("", "2em")], None, False, True) == 0


def test_urls_keep_their_quotes() -> None:
    css = ".a { background: url(a.png) } .b { mask: url('b c.svg') }"

    assert rewrite_urls(css, "/root/".__add__) == (
        '.a { background: url(/root/a.png) } .b { mask: url("/root/b c.svg") }'
    )
    assert rewrite_urls("fill: url(#g)", str.upper) == "fill: url(#G)"


def test_ids_of_selectors_and_references_are_renamed() -> None:
    def rename(id: str) -> str:
        return "p1-" + id if id in {"target", "grad", "abc"} else id

    css = rewrite_ids(
        "#target, .x > #fff { color: #abc; fill: url(#grad) }"
        " @media print { .a #target { margin: 0 } }"
        " .n { & #abc { color: red } }",
        rename,
    )

    assert "#p1-target, .x > #fff {" in css
    assert "color: #abc" in css
    assert "url(#p1-grad)" in css
    assert ".a #p1-target {" in css
    assert "& #p1-abc {" in css
    assert rename_selector_ids("#target > code", rename) == "#p1-target > code"


def test_page_rules_are_taken_out_at_any_depth() -> None:
    rules, rest = split_page_rules(
        "@page :first { margin: 0; } .x { color: red; }"
        " @media print { @page cover:left, x { margin: 1cm } .y { color: blue } }"
    )

    assert rules == [
        PageRule([":first"], "{ margin: 0; }"),
        PageRule(["cover:left", "x"], "{ margin: 1cm }"),
    ]
    assert "@page" not in rest
    assert ".x { color: red; }" in rest
    assert ".y { color: blue; }" in rest


def test_pages_are_renamed() -> None:
    css = rename_pages(".a { page: last; } .b { page: other; }", {"last": "last-1"})

    assert "page: last-1" in css
    assert "page: other" in css


def test_scoped_styles_keep_global_at_rules() -> None:
    css = scope("@font-face { font-family: X; } .title { color: red; }", "#part")

    assert css.startswith("@font-face { font-family: X; }")
    assert "@scope (#part) {\n.title { color: red; }\n}" in css
    assert scope("@keyframes k { from {} }", "#part") == "@keyframes k { from {} }"


@pytest.mark.parametrize(
    "css",
    [".a { color red }", ".a, .b", "@page :first { margin: 0 } }"],
)
def test_invalid_stylesheets_are_left_as_they_are(css: str) -> None:
    rules, rest = split_page_rules(css)

    assert rewrite_ids(css, "p-".__add__) == css
    assert rename_pages(css, {"x": "y"}) == css
    assert rules == []
    assert rest == css
    assert css in scope(css, "#part")


def test_invalid_blocks_keep_their_content() -> None:
    css = rewrite_ids(".a { *zoom: 1; fill: url(#t) } #t { color: red }", "p-".__add__)

    assert css == ".a { *zoom: 1; fill: url(#p-t) } #p-t { color: red; }"


def test_unchanged_stylesheets_are_not_serialized_again() -> None:
    css = ".a{color:red}.b>#c{fill:url(#d)}@media print{.e{page:x}}"

    assert rewrite_urls(css, str) == css
    assert rewrite_ids(css, str) == css
    assert rename_selector_ids("#c>d", str) == "#c>d"
    assert rename_pages(css, {"other": "y"}) == css
    assert split_page_rules(css) == ([], css)
