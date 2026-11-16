from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from mkdocs_exporter.standalone.cli import main
from tests.support.pdf import OutlineItem, PdfDocument

pytest.importorskip("zensical")

pytestmark = pytest.mark.browser

FIXTURE = Path(__file__).parent.parent / "fixtures" / "site"

EXPORTER = """
plugins:
  - exporter:
      formats:
        pdf:
          stylesheets: [pdf.css]
          covers: {front: covers/front.html, back: covers/back.html}
          books:
            - output: book.pdf
              covers: none
              toc: {enabled: true}
"""


def titles(items: list[OutlineItem]) -> list[Any]:
    """The titles of bookmarks, with those of their children."""

    return [[i.title, titles(i.children)] if i.children else i.title for i in items]


class Website:
    """A copy of the fixture project, built by Zensical."""

    def __init__(self, path: Path, config: str = "mkdocs.yml") -> None:
        shutil.copytree(FIXTURE, path)

        self.path = path
        self.config = path / config

    def write(self, path: str, content: str) -> None:
        target = self.path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def build(self, engine: str = "zensical") -> None:
        subprocess.run(
            [sys.executable, "-m", engine, "build", "-f", str(self.config)],
            check=True,
            capture_output=True,
            cwd=self.path,
        )

    def export(self, *args: str) -> Result:
        return CliRunner().invoke(main, ["build", "-f", str(self.config), *args])

    def pdfs(self) -> list[str]:
        site = self.path / "site"

        return sorted(p.relative_to(site).as_posix() for p in site.rglob("*.pdf"))

    def pdf(self, path: str) -> PdfDocument:
        return PdfDocument(self.path / "site" / path)

    def html(self, path: str) -> str:
        return (self.path / "site" / path).read_text(encoding="utf-8")


@pytest.fixture
def website(tmp_path: Path) -> Website:
    website = Website(tmp_path / "project")
    website.write(
        "mkdocs.yml", (FIXTURE / "mkdocs.yml").read_text(encoding="utf-8") + EXPORTER
    )

    return website


def test_documents_and_books_of_a_zensical_website(website: Website) -> None:
    website.build()
    result = website.export()

    assert result.exit_code == 0, result.output
    assert website.pdfs() == [
        "book.pdf",
        "guide/advanced/index.pdf",
        "guide/intro/index.pdf",
        "index.pdf",
        "reference/index.pdf",
    ]

    intro = website.pdf("guide/intro/index.pdf")
    book = website.pdf("book.pdf")

    assert intro.count("FRONT-COVER") == 1
    assert "TAB-TWO-MARKER" in intro.text
    assert titles(book.outline) == [
        "Home",
        [
            "Guide",
            [
                ["Introduction", ["Lorem"]],
                ["Advanced", [["Deep dive", ["Sub section"]], "Another section"]],
            ],
        ],
        "Reference",
    ]
    assert "Table of contents" in book.pages_text[0]


def test_content_meant_for_documents_only(website: Website) -> None:
    website.write(
        "docs/reference.md",
        '# Reference\n\n<div id="target"></div>\n\n'
        '<p class="mkdocs-exporter-only">ONLY-MARKER</p>\n\n'
        '<span data-mkdocs-exporter-teleport="#target">TELEPORT-MARKER</span>\n',
    )
    website.build()

    assert website.export().exit_code == 0

    html = website.html("reference/index.html")

    assert "ONLY-MARKER" in website.pdf("reference/index.pdf").text
    assert "ONLY-MARKER" not in html
    assert 'id="target"><span>TELEPORT-MARKER</span>' in html

    again = website.export()

    assert again.exit_code == 1
    assert "already exported" in again.output


def test_front_matter_and_meta_files(website: Website) -> None:
    config = website.config.read_text(encoding="utf-8")
    website.write("mkdocs.yml", config.replace("plugins:\n", "plugins:\n  - meta\n", 1))
    website.write("docs/guide/.meta.yml", "exporter:\n  pdf:\n    enabled: false\n")
    website.write(
        "docs/reference.md",
        "---\nexporter: {pdf: {covers: {enabled: false}}}\n---\n\n# Reference\n",
    )
    website.build()

    assert website.export().exit_code == 0
    assert website.pdfs() == ["book.pdf", "index.pdf", "reference/index.pdf"]
    assert website.pdf("reference/index.pdf").count("FRONT-COVER") == 0


def test_zensical_toml(tmp_path: Path) -> None:
    """Without `nav`, documents follow the navigation of the built pages."""

    website = Website(tmp_path / "project", config="zensical.toml")
    website.write(
        "zensical.toml",
        "[project]\nsite_name = 'Fixture'\nsite_url = 'https://example.org/docs/'\n"
        "use_directory_urls = false\n\n"
        "[project.plugins.exporter.formats.pdf]\n"
        "books = [{ output = 'book.pdf', covers = 'none' }]\n",
    )
    website.build()
    result = website.export()

    assert result.exit_code == 0, result.output
    assert website.pdfs() == [
        "book.pdf",
        "guide/advanced.pdf",
        "guide/intro.pdf",
        "index.pdf",
        "reference.pdf",
    ]
    outline = website.pdf("book.pdf").outline

    assert [item.title for item in outline] == ["Home", "Reference", "Guide"]
    assert [item.title for item in outline[2].children] == ["Advanced", "Introduction"]


def test_websites_built_by_mkdocs_are_refused(website: Website) -> None:
    website.write("mkdocs.yml", (FIXTURE / "mkdocs.yml").read_text(encoding="utf-8"))
    website.build("mkdocs")
    result = website.export()

    assert result.exit_code == 1
    assert "list the plugin in 'plugins' instead" in result.output
    assert website.pdfs() == []


def test_strict_mode_fails_on_warnings(website: Website) -> None:
    config = website.config.read_text(encoding="utf-8")
    website.write(
        "mkdocs.yml",
        config + "      buttons:\n        - title: B\n          icon: material-star\n",
    )
    website.build()
    result = website.export("--strict")

    assert result.exit_code == 1
    assert "Aborted with 1 warning(s) in strict mode" in result.output
