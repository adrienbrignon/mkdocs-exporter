"""Tests of the HTML helpers."""

import pytest

from mkdocs_exporter.core.html import HtmlDocument, resolve_link

BASE = "https://example.org/docs/"


@pytest.mark.parametrize(
    ("href", "page", "expected"),
    [
        ("guide/intro/", "", BASE + "guide/intro/"),
        ("../advanced/#deep-dive", "guide/intro/", BASE + "guide/advanced/#deep-dive"),
        ("../index.html", "guide/intro.html", BASE + "index.html"),
        ("intro.html?x=1", "guide/advanced.html", BASE + "guide/intro.html?x=1"),
        ("/docs/reference/", "guide/intro/", BASE + "reference/"),
        ("/assets/file.zip", "guide/intro/", BASE + "assets/file.zip"),
        ("#anchor", "guide/intro/", None),
        ("", "guide/intro/", None),
        ("mailto:someone@example.org", "", None),
        ("tel:+33100000000", "", None),
        ("data:text/plain,hello", "", None),
        ("javascript:void(0)", "", None),
        ("https://other.example.org/", "", None),
        ("//cdn.example.org/lib.js", "", None),
    ],
)
def test_resolve_link(href: str, page: str, expected: str | None) -> None:
    assert resolve_link(href, page, "/docs/", BASE) == expected


def test_resolve_link_replaces_the_root_with_another_base() -> None:
    assert (
        resolve_link("guide/intro/", "", "/docs/", "https://pdf.example.com/")
        == "https://pdf.example.com/guide/intro/"
    )


def test_teleport_moves_elements_to_their_destination() -> None:
    html = HtmlDocument(
        '<html><head></head><body><style data-teleport="head">a{}</style></body></html>'
    )

    html.teleport()

    assert str(html.soup.head) == "<head><style>a{}</style></head>"


def test_teleport_keeps_elements_without_destination() -> None:
    html = HtmlDocument('<body><p data-teleport="#missing">x</p></body>')

    html.teleport()

    assert html.select_one("p") is not None


def test_scripts_can_be_inserted_first_in_the_head() -> None:
    html = HtmlDocument("<html><head><script>a</script></head><body></body></html>")

    html.add_script("b", head=True, first=True)

    assert [s.string for s in html.select("head script")] == ["b", "a"]


def test_data_cannot_close_the_script_element() -> None:
    html = HtmlDocument("<body></body>")

    html.add_data("DATA", {"value": "</script><script>alert(1)</script>"})

    assert len(html.select("script")) == 1
