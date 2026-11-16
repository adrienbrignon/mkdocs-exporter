import json
from pathlib import Path

import pytest

from mkdocs_exporter.core.books import NavNode
from mkdocs_exporter.standalone import site
from mkdocs_exporter.standalone.project import ProjectError, load
from mkdocs_exporter.standalone.site import BuiltPage, Source, url_of

GENERATOR = '<meta name="generator" content="zensical-0.1.1">'


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return path


def page(url: str, prev: str | None = None, next: str | None = None) -> BuiltPage:
    links = "".join(
        f'<link rel="{rel}" href="{href}">'
        for rel, href in (("prev", prev), ("next", next))
        if href is not None
    )

    return BuiltPage(
        file=Source(url.rstrip("/") + ".md" if url else "index.md"),
        url=url,
        title=url or "Home",
        path=Path("unused"),
        html=f"<html><head>{links}</head><body></body></html>",
    )


def titles(nodes: list[NavNode]) -> list:
    return [
        [node.title, titles(node.children)] if node.children else node.title
        for node in nodes
    ]


@pytest.mark.parametrize(
    ("source", "directories", "expected"),
    [
        ("index.md", True, ""),
        ("README.md", True, ""),
        ("guide/intro.md", True, "guide/intro/"),
        ("guide/index.md", True, "guide/"),
        ("index.md", False, "index.html"),
        ("guide/intro.md", False, "guide/intro.html"),
        ("guide/README.md", False, "guide/index.html"),
    ],
)
def test_urls_of_pages(source: str, directories: bool, expected: str) -> None:
    assert url_of(source, directories) == expected


def test_pages_follow_their_next_links() -> None:
    pages = [
        page("guide/b/", prev="../../", next="../a/"),
        page("", next="./guide/b/"),
        page("orphan/"),
        page("guide/a/", prev="../b/"),
    ]

    assert [p.url for p in site._chain(pages)] == ["", "guide/b/", "guide/a/"]


def test_links_going_round_in_circles_stop() -> None:
    pages = [page("", next="a/"), page("a/", prev="../", next="../")]

    assert [p.url for p in site._chain(pages)] == ["", "a/"]
    assert site._chain([page(""), page("a/")]) == []


def test_sections_group_consecutive_pages() -> None:
    pages = [page(""), page("a/"), page("b/"), page("c/"), page("d/")]
    pages[1].sections = ["Guide"]
    pages[2].sections = ["Guide", "Deep"]
    pages[3].sections = ["Guide"]

    assert titles(site._sectioned(pages)) == [
        "Home",
        ["Guide", ["a/", ["Deep", ["b/"]], "c/"]],
        "d/",
    ]


def test_the_configured_navigation() -> None:
    pages = {p.file.src_uri: p for p in (page(""), page("a/"), page("b/"))}
    nav = [
        "index.md",
        {"Section": ["a.md", {"Custom": "b.md"}, {"Link": "https://example.org"}]},
        {"Missing": "missing.md"},
    ]

    nodes = site._configured(nav, pages)

    assert titles(nodes) == ["Home", ["Section", ["a/", "Custom"]]]
    assert site.documents(nodes) == ["index.md", "a.md", "b.md"]


def test_websites_built_by_mkdocs_are_refused() -> None:
    built = page("")
    built.html = '<meta name="generator" content="mkdocs-1.6.1, mkdocs-material-9.8.1">'

    with pytest.raises(ProjectError, match=r"built by mkdocs-1\.6\.1: list the plugin"):
        site._check_generator([built])

    built.html = GENERATOR
    site._check_generator([built])


def test_pages_of_a_built_website(tmp_path: Path, exporter_logs) -> None:
    project = load(write(tmp_path / "zensical.toml", "[project]\nsite_name = 'S'\n"))
    write(tmp_path / "docs/index.md", "# Home\n")
    write(tmp_path / "docs/guide/a.md", "---\ntitle: Alpha\npdf: true\n---\n# A\n")
    write(tmp_path / "docs/excluded.md", "# Excluded\n")
    write(tmp_path / "site/index.html", f"<html><head>{GENERATOR}</head></html>")
    write(tmp_path / "site/guide/a/index.html", "<html><head></head></html>")
    write(tmp_path / "site/generated/index.html", "<html></html>")
    write(
        tmp_path / "site/search.json",
        json.dumps(
            {
                "items": [
                    {"location": "", "title": "Home", "path": ["Home"]},
                    {"location": "guide/a/", "title": "Alpha", "path": ["Guide", "A"]},
                    {"location": "guide/a/#a", "title": "A", "path": ["Guide", "A"]},
                    {"location": "generated/", "title": "Generated", "path": ["G"]},
                ]
            }
        ),
    )

    pages = site.pages(project)

    assert [(p.file.src_uri, p.url, p.title, p.sections) for p in pages] == [
        ("index.md", "", "Home", []),
        ("guide/a.md", "guide/a/", "Alpha", ["Guide"]),
    ]
    assert pages[1].meta == {"title": "Alpha", "pdf": True}
    assert any(
        "No source file for the built page 'generated/'" in m for m in exporter_logs()
    )


def test_meta_files_give_defaults_to_front_matter(tmp_path: Path) -> None:
    project = load(
        write(tmp_path / "zensical.toml", "[project]\n[project.plugins.meta]\n")
    )
    write(tmp_path / "docs/.meta.yml", "exporter: {pdf: {enabled: false}}\ntags: [a]\n")
    write(tmp_path / "docs/guide/.meta.yml", "tags: [b]\nauthor: Guide\n")
    write(tmp_path / "docs/guide/a.md", "---\nauthor: Page\ntags: [c]\n---\n# A\n")

    assert site._front_matter(project, "guide/a.md") == {
        "exporter": {"pdf": {"enabled": False}},
        "tags": ["a", "b", "c"],
        "author": "Page",
    }
