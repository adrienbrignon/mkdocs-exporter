from bs4 import BeautifulSoup

from mkdocs_exporter.core.books.assembly import Part, part_element, reuse
from mkdocs_exporter.core.books.ids import collect_ids, namespace_ids
from mkdocs_exporter.core.books.styles import (
    FRONT_COVER_PAGE,
    PageNames,
    part_styles,
    structure,
    translate_page_rules,
)
from mkdocs_exporter.core.books.urls import rewrite_urls, site_path
from mkdocs_exporter.core.document import Document
from mkdocs_exporter.core.html import (
    HtmlDocument,
    PageResources,
    resource_url,
    teleported,
)
from mkdocs_exporter.core.preparation import Prepared

FRAGMENT = """<article>
<img src="../img/a.png" srcset="../img/a.png 1x, ../img/a@2x.png 2x">
<video src="v.mp4" poster="p.jpg"></video><object data="o.svg"></object>
<div style="background: url('../bg.png')"></div>
<style>.x { background: url(../s.png); } #target { color: red } #fff {}</style>
<svg><defs><linearGradient id="grad"></linearGradient></defs>
  <use href="#icon"/><use xlink:href="sprite.svg#icon2"/>
  <path id="icon" fill="url(#grad)" style="stroke: url('#grad')"/></svg>
<img usemap="#map"><map name="map"><area href="../other/#sec" shape="rect"></map>
<label for="in">L</label><input id="in" list="dl"><datalist id="dl"></datalist>
<div aria-labelledby="in target missing"></div>
<input type="radio" name="__tabbed_1" id="__tabbed_1_1"><input type="checkbox" name="keep">
<table><tr><th id="h">H</th></tr><tr><td headers="h">D</td></tr></table>
<p id="target"><a href="#target">self</a> <a href="#nope">dangling</a>
<a href="https://example.org/x">external</a> <a href="mailto:a@b.c">mail</a>
<a href="../other/#sec">other part</a> <a href="/">root</a></p>
</article>"""


def rewritten() -> str:
    article = BeautifulSoup(FRAGMENT, "lxml").article
    assert article is not None

    namespace_ids(article, "p1-", collect_ids(article))
    rewrite_urls(
        article,
        "guide/page/",
        "/docs/",
        lambda path, fragment: f"[{path}#{fragment}]",
    )

    return str(article)


def test_resources_become_root_absolute() -> None:
    html = rewritten()

    for expected in [
        'src="/docs/guide/img/a.png"',
        'srcset="/docs/guide/img/a.png 1x, /docs/guide/img/a@2x.png 2x"',
        'src="/docs/guide/page/v.mp4"',
        'poster="/docs/guide/page/p.jpg"',
        'data="/docs/guide/page/o.svg"',
        'url("/docs/guide/bg.png")',
        "url(/docs/guide/s.png)",
        'xlink:href="/docs/guide/page/sprite.svg#icon2"',
    ]:
        assert expected in html


def test_links_are_resolved_against_their_page() -> None:
    html = rewritten()

    assert 'href="[guide/other/#sec]"' in html
    assert 'href="[#]"' in html
    assert 'href="https://example.org/x"' in html
    assert 'href="mailto:a@b.c"' in html


def test_identifiers_and_references_are_namespaced() -> None:
    html = rewritten()

    for expected in [
        'id="p1-grad"',
        'href="#p1-icon"',
        'fill="url(#p1-grad)"',
        'stroke: url("#p1-grad")',
        'usemap="#p1-map"',
        'name="p1-map"',
        'for="p1-in"',
        'list="p1-dl"',
        'aria-labelledby="p1-in p1-target missing"',
        'name="p1-__tabbed_1"',
        'name="keep"',
        'headers="p1-h"',
        'href="#p1-target"',
        'href="#nope"',
        "#p1-target { color: red",
        "#fff {}",
    ]:
        assert expected in html


def test_resource_and_site_paths() -> None:
    assert (
        resource_url("data:image/png;base64,x", "a/", "/") == "data:image/png;base64,x"
    )
    assert resource_url("/root.png", "a/", "/docs/") == "/root.png"
    assert site_path("../b/index.html#x", "a/", "/docs/") == ("b/", "x")
    assert site_path("#x", "a/", "/docs/") is None
    assert site_path("https://example.org/", "a/", "/docs/") is None


def test_first_page_rules_target_the_cover() -> None:
    pages, rest = translate_page_rules(
        "@page :first { margin: 0; } @page { size: A4; } .x { color: red; }",
        ["cover"],
    )

    assert pages == "@page cover { margin: 0; }\n@page  { size: A4; }"
    assert ".x { color: red; }" in rest


def test_page_rules_of_a_part_get_its_own_pages() -> None:
    pages, rest = translate_page_rules(
        "@page { color: red; } @page last { margin: 0; } .back { page: last; }",
        ["cover-1"],
        ["part-1", "cover-1"],
        {"last": "last-1"},
    )

    assert "@page part-1 { color: red; }" in pages
    assert "@page cover-1 { color: red; }" in pages
    assert "@page last-1 { margin: 0; }" in pages
    assert "page: last-1" in rest


def part(index: int, styles: list[str], covers: set[str] | None = None) -> Part:
    html = HtmlDocument("<article></article>")
    content = html.select_one("article")
    assert content is not None

    return Part(
        index=index,
        document=Document(id=str(index), url=f"{index}/", path=f"{index}.pdf"),
        covers=covers or set(),
        html=html,
        content=content,
        styles=styles,
    )


def test_identical_styles_of_parts_are_shared() -> None:
    styles, names = part_styles([part(0, ["@page :first { margin: 0; }"])] * 2)

    assert styles == ["\n@page mkdocs-exporter-front-cover { margin: 0; }"]
    assert set(names.front.values()) == {FRONT_COVER_PAGE}
    assert names.content == {}


def test_styles_differing_between_parts_are_scoped() -> None:
    parts = [
        part(0, [".t::after { content: 'A'; }"]),
        part(1, [".t::after { content: 'B'; }"]),
    ]

    styles, names = part_styles(parts)

    assert "@scope (#mkdocs-exporter-part-0)" in styles[0]
    assert "@scope (#mkdocs-exporter-part-1)" in styles[1]
    assert names.front["mkdocs-exporter-part-1"] == f"{FRONT_COVER_PAGE}-1"
    assert names.content["mkdocs-exporter-part-1"] == "mkdocs-exporter-part-1"


def test_parts_are_named_after_their_first_page() -> None:
    names = PageNames()
    parts = [part(0, [], {"front"}), part(1, [])]
    names.complete(parts, toc=True, titled=True)
    css = structure(parts, names)

    assert names.first == {
        "mkdocs-exporter-part-0": FRONT_COVER_PAGE,
        "mkdocs-exporter-part-1": "mkdocs-exporter-part-1",
    }
    assert f"body {{ page: {FRONT_COVER_PAGE}; }}" in css
    assert (
        ":where(#mkdocs-exporter-part-1) > * { page: mkdocs-exporter-part-1; }" in css
    )


def test_prepared_content_keeps_the_covers_of_the_part() -> None:
    html = HtmlDocument(
        '<article><div class="mkdocs-exporter-front-cover">'
        '<style data-mkdocs-exporter-teleport="head">.front {}</style>FRONT</div><p>Text</p>'
        '<style data-mkdocs-exporter-teleport="head">.page {}</style>'
        '<div class="mkdocs-exporter-back-cover">'
        '<style data-mkdocs-exporter-teleport="head">.back {}</style>BACK</div></article>'
    )
    content = html.select_one("article")
    assert content is not None

    moved = teleported(content)
    prepared = Prepared(content=content, resources=PageResources(), teleported=moved)
    part = reuse(1, Document(id="a", url="a/", path="a.pdf"), {"front"}, prepared)

    assert [origin for origin, _, _ in moved] == ["front", "content", "back"]
    assert part.prepared
    assert part.styles == [".front {}", ".page {}"]
    assert "FRONT" in part.content.get_text()
    assert "BACK" not in part.content.get_text()


def test_resolved_links_lead_to_parts() -> None:
    article = BeautifulSoup(
        '<article><a href="https://example.org/docs/b/#x">B</a></article>', "lxml"
    ).article
    assert article is not None

    rewrite_urls(
        article,
        "a/",
        "/docs/",
        lambda path, fragment: f"[{path}#{fragment}]",
        "https://example.org/docs/",
    )

    assert 'href="[b/#x]"' in str(article)


def test_part_element_of_themes_without_content_element() -> None:
    html = HtmlDocument(
        "<html><body><p>Text</p><script>run()</script><nav>Nav</nav></body></html>"
    )
    article = HtmlDocument("<html><body><article><p>Text</p></article></body></html>")

    element = part_element(html, html.body)

    assert element.name == "div"
    assert str(element) == "<div><p>Text</p><nav>Nav</nav></div>"
    assert (
        str(html.body)
        == "<body><div><p>Text</p><nav>Nav</nav></div><script>run()</script></body>"
    )
    assert part_element(article, article.soup.article) is article.soup.article
