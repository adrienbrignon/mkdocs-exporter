"""End-to-end tests of the example projects shown by the documentation (`examples/`).

Each example is built from a copy of `examples/`, and checked against what the
documentation says it does.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.conftest import Site

pytest.importorskip("material", reason="The examples use Material for MkDocs")

from mkdocs.commands.build import build
from mkdocs.config import load_config

pytestmark = pytest.mark.browser

EXAMPLES = Path(__file__).parents[2] / "examples"


def squeeze(text: str) -> str:
    """A text without whitespace: lines wrap differently with other fonts."""

    return "".join(text.split())


@pytest.fixture(scope="module")
def example(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], Site]:
    """Builds an example project (once per module)."""

    root = tmp_path_factory.mktemp("examples") / "examples"
    sites: dict[str, Site] = {}

    shutil.copytree(EXAMPLES, root, ignore=shutil.ignore_patterns("*.pdf", ".cache"))

    def get(name: str) -> Site:
        if name not in sites:
            config = load_config(
                config_file=str(root / name / "mkdocs.yml"),
                site_dir=str(root / name / "site"),
            )

            config.plugins.on_startup(command="build", dirty=False)

            try:
                build(config)
            finally:
                config.plugins.on_shutdown()

            sites[name] = Site(project=root / name, path=Path(config.site_dir))

        return sites[name]

    return get


def test_every_example_is_tested() -> None:
    projects = {path.parent.name for path in EXAMPLES.glob("*/mkdocs.yml")}
    tests = {
        name.removeprefix("test_").replace("_", "-")
        for name in globals()
        if name.startswith("test_") and name != "test_every_example_is_tested"
    }

    assert projects == tests


def test_field_guide(example: Callable[[str], Site]) -> None:
    site = example("field-guide")
    combined = site.pdf("field-guide.pdf")

    writing = squeeze(site.pdf("guide/writing/index.pdf").pages_text[0])

    assert "Anexampleofdocuments" in squeeze(combined.pages_text[0])
    assert "FIELDGUIDEGuideFIELDGUIDEwriting-pages" in writing
    assert "SECTIONS01Textandlists" in writing
    assert "Table of contents" in combined.pages_text[1]
    assert [item.title for item in combined.outline] == [
        "Welcome",
        "Guide",
        "Reference",
    ]
    assert "Anexampleofdocuments" in squeeze(combined.pages_text[-1])
    assert len(site.pdfs()) == 6


def test_page_numbers(example: Callable[[str], Site]) -> None:
    document = example("page-numbers").pdf("guide/writing/index.pdf")
    pages = document.page_count

    assert pages > 1

    for index, text in enumerate(document.pages_text, 1):
        assert "Field Guide" in text
        assert f"Page {index} of {pages}" in text


def test_cover_pages(example: Callable[[str], Site]) -> None:
    document = example("cover-pages").pdf("guide/writing/index.pdf")
    cover, contents = document.pages_text[:2]

    assert "Version2.4.0WritingpagesText,lists,code,admonitions" in squeeze(cover)
    assert "Contents" in contents
    assert "Text and lists" in contents


def test_book(example: Callable[[str], Site]) -> None:
    document = example("book").pdf("field-guide.pdf")
    titles = ["Welcome", "Writing pages", "Printing pages", "Paper sizes", "Glossary"]
    starts = [
        next(i for i, text in enumerate(document.pages_text) if title in text[:40])
        for title in titles[1:]
    ]
    sizes = {
        (round(float(page.mediabox.width)), round(float(page.mediabox.height)))
        for page in document.reader.pages
    }

    assert sizes == {(432, 648)}
    assert "Contents" in document.pages_text[1]
    assert all(start % 2 == 0 for start in starts), starts
    assert [item.title for item in document.outline] == [
        "Welcome",
        "Guide",
        "Reference",
    ]


def test_page_layout(example: Callable[[str], Site]) -> None:
    document = example("page-layout").pdf("reference/paper-sizes/index.pdf")
    sizes = [
        (round(float(page.mediabox.width)), round(float(page.mediabox.height)))
        for page in document.reader.pages
    ]
    landscape = sizes.index((792, 612))

    assert sizes[0] == (612, 792)
    assert sizes[landscape + 1] == (612, 792)
    assert "CSSkeyword" in squeeze(document.pages_text[landscape])
    assert "ledger" in document.pages_text[landscape]


def test_print_styles(example: Callable[[str], Site]) -> None:
    site = example("print-styles")
    glossary = squeeze(site.pdf("reference/glossary/index.pdf").text)
    writing = site.pdf("guide/writing/index.pdf")
    home = site.pdf("index.pdf").text

    assert "1.Pages" in glossary
    assert "(https://www.w3.org/TR/css-page-3/#margin-boxes)" in glossary
    assert "(https://field-guide.example.com/guide/printing/)" in squeeze(writing.text)
    assert all("DRAFT" in text for text in writing.pages_text)
    assert "printed from the Field Guide website" in home
    assert "Download" not in home
    assert "printed from the Field Guide website" not in site.html("index.html")


def test_toc_template(example: Callable[[str], Site]) -> None:
    document = example("toc-template").pdf("field-guide.pdf")
    contents = squeeze(document.pages_text[0])
    glossary = document.pages_containing("Widows")[0]

    assert contents.startswith("Contents")
    assert f"Glossary{glossary + 1}Pages" in contents
    assert document.links[0].target_page is not None


def test_documents(example: Callable[[str], Site]) -> None:
    site = example("documents")
    everything = site.pdf("pdf/field-guide.pdf").text
    guide = site.pdf("pdf/guide.pdf")
    reference = site.pdf("pdf/reference.pdf")

    assert "Welcome" not in everything
    assert "Writing pages" in everything
    assert "Glossary" in everything
    assert "Writing pages" in guide.text
    assert "Paper sizes" not in guide.text
    assert "Paper sizes" in reference.text
    assert "Writing pages" not in reference.text
    assert guide.metadata["/Title"] == "Field Guide - Guide"
    assert f"Page 1 of {guide.page_count}" in guide.pages_text[0]
