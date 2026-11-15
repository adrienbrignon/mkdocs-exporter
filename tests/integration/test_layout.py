"""End-to-end tests of how pages are laid out by the browser."""

from __future__ import annotations

import re

import pytest

from tests.conftest import Project
from tests.support.pdf import PdfDocument

pytestmark = pytest.mark.browser

WIDE = """# Reference

<div style="width: 3000px">Wide content.</div>

```
{line}
```
""".format(line="x" * 500)


@pytest.mark.parametrize("theme", ["material", "readthedocs"])
def test_wide_content_does_not_shrink_pages(project: Project, theme: str) -> None:
    """Content wider than pages is cut off instead of shrinking every page."""

    project.write("docs/reference.md", WIDE)

    site = project.build(theme={"name": theme})
    expected = site.pdf("guide/intro/index.pdf").font_size("Introduction")

    assert expected is not None
    assert site.pdf("reference/index.pdf").font_size("Reference") == expected


def test_pages_of_different_widths_do_not_shrink_pages(project: Project) -> None:
    """A first page without margins doesn't shrink Material's layout."""

    project.write("narrow.css", "@page :first { margin: 0; }")

    expected = project.build().pdf("guide/intro/index.pdf").font_size("Introduction")
    site = project.build(
        exporter={"formats": {"pdf": {"stylesheets": ["pdf.css", "narrow.css"]}}}
    )

    assert expected is not None
    assert site.pdf("guide/intro/index.pdf").font_size("Introduction") == expected


def fills(document: PdfDocument, page: int) -> list[str]:
    """The colors a page is filled with, in order (`r g b`)."""

    data = document.reader.pages[page].get_contents().get_data().decode("latin-1")

    return re.findall(r"([\d.]+ [\d.]+ [\d.]+) rg", data)


@pytest.mark.parametrize("path", ["index.pdf", "combined.pdf"])
def test_page_backgrounds_are_not_hidden_by_the_website(
    project: Project, path: str
) -> None:
    """Material's opaque body would be painted over a full-bleed cover's background."""

    project.write("red.css", "@page :first { margin: 0; background: #f00; }")

    site = project.build(
        exporter={"formats": {"pdf": {"stylesheets": ["pdf.css", "red.css"]}}}
    )
    colors = fills(site.pdf(path), 0)

    assert colors[0] == "1 0 0"
    assert "1 1 1" not in colors
