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


SLATE = {"name": "material", "palette": {"scheme": "slate"}}
"""Material's dark scheme (for screens only: printed on white)."""

DARK = (30 / 255, 33 / 255, 41 / 255)
"""The background of Material's dark scheme on screens."""

COVER = "@page :first { margin: 0; background: #f00; }"


def filled(document: PdfDocument, page: int, color: tuple[float, ...]) -> bool:
    """Is a page filled with a color (anywhere)?"""

    return any(
        all(abs(float(a) - b) < 0.01 for a, b in zip(fill.split(), color, strict=True))
        for fill in fills(document, page)
    )


@pytest.mark.parametrize("css", [COVER, f"@media print {{ {COVER} }}"])
def test_page_backgrounds_are_not_hidden_by_the_website(
    project: Project, css: str
) -> None:
    """Material's opaque body would be painted over a full-bleed cover's background."""

    project.write("red.css", css)

    site = project.build(
        exporter={"formats": {"pdf": {"stylesheets": ["pdf.css", "red.css"]}}},
        theme=SLATE,
    )

    for path in ("index.pdf", "combined.pdf"):
        document = site.pdf(path)

        assert fills(document, 0)[0] == "1 0 0"
        assert "1 1 1" not in fills(document, 0)
        assert not filled(document, 1, DARK)


def test_dark_themes_are_printed_on_their_print_background(project: Project) -> None:
    """The background of the website is only dropped for pages that have their own."""

    site = project.build(theme=SLATE)

    for path in ("index.pdf", "combined.pdf"):
        document = site.pdf(path)

        assert not any(
            filled(document, page, DARK) for page in range(len(document.reader.pages))
        )


def test_print_backgrounds_of_the_website_are_kept(project: Project) -> None:
    project.write("docs/print.css", "@media print { body { background: #0f0; } }")

    site = project.build(extra_css=["print.css"])

    for path in ("index.pdf", "combined.pdf"):
        assert "0 1 0" in fills(site.pdf(path), 1)
