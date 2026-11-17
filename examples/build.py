from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / ".cache" / "examples"
IMAGES = ROOT.parent / "docs" / "assets" / "images" / "examples"

PREVIEWS: dict[str, list[tuple[str, int, str]]] = {
    "field-guide": [
        ("field-guide.pdf", 1, "The cover of the book"),
        ("field-guide.pdf", 2, "Its table of contents"),
        ("field-guide.pdf", 4, "One of its pages"),
        ("guide/writing/index.pdf", 3, "A page printed with the material theme"),
        ("guide/writing/index.pdf", 1, "The front cover of a page's document"),
        ("guide/writing/index.pdf", -1, "The back cover of a page's document"),
    ],
    "field-guide-readthedocs": [
        ("guide/writing/index.pdf", 3, "The page printed with the readthedocs theme"),
    ],
    "page-numbers": [
        ("guide/writing/index.pdf", 1, "A page with a header and a footer"),
    ],
    "cover-pages": [
        ("guide/writing/index.pdf", 1, "The front cover"),
        ("guide/writing/index.pdf", 2, "The table of contents"),
    ],
    "book": [
        ("field-guide.pdf", 1, "The cover"),
        ("field-guide.pdf", 2, "The table of contents"),
        ("field-guide.pdf", 8, "A blank left-hand page"),
        ("field-guide.pdf", 9, "A chapter starting on a right-hand page"),
    ],
    "page-layout": [
        ("reference/paper-sizes/index.pdf", 1, "A portrait page"),
        ("reference/paper-sizes/index.pdf", 2, "A table on a landscape page"),
    ],
    "print-styles": [
        (
            "reference/glossary/index.pdf",
            1,
            "Numbered headings, link addresses and a watermark",
        ),
    ],
    "documents": [
        ("pdf/field-guide.pdf", 1, "The table of contents of the whole guide"),
    ],
    "toc-template": [
        ("field-guide.pdf", 1, "A table of contents laid out as a table"),
    ],
}
"""The pages shown by the documentation, by site: (document, page number counted from
the end when negative, caption)."""

DOCUMENTS: dict[str, list[str]] = {
    "documents": ["pdf/guide.pdf", "pdf/reference.pdf"],
}
"""The documents published with the documentation, besides those of `PREVIEWS`."""

SITES = [
    *((path.parent.name, None) for path in sorted(ROOT.glob("*/mkdocs.yml"))),
    ("field-guide", "readthedocs"),
]
"""The sites to build: (project, theme replacing the project's)."""

RESOLUTION = 72
"""The resolution of previews (dots per inch)."""


class BuildError(Exception):
    """An example project failed to build."""


def name(project: str, theme: str | None) -> str:
    """The name of a site."""

    return f"{project}-{theme}" if theme else project


def documents(site: str) -> list[str]:
    """The documents of a site published with the documentation."""

    shown = [document for document, _, _ in PREVIEWS.get(site, [])]

    return list(dict.fromkeys([*shown, *DOCUMENTS.get(site, [])]))


def build(project: str, theme: str | None = None) -> Path:
    """Builds a project, returning its site directory."""

    site = OUTPUT / name(project, theme)
    command = [
        *(sys.executable, "-m", "properdocs", "build", "--strict"),
        *("--config-file", str(ROOT / project / "mkdocs.yml")),
        *("--site-dir", str(site)),
        *(("--theme", theme) if theme else ()),
    ]
    result = subprocess.run(command, capture_output=True, text=True)  # noqa: S603

    if result.returncode:
        raise BuildError(f"Failed to build {name(project, theme)}:\n{result.stderr}")

    return site


def build_all(jobs: int = 4) -> dict[str, Path]:
    """Builds every site, returning their directories by name.

    Projects are built concurrently, the sites of a project one after the other (they
    share the project's cache).
    """

    def project_sites(project: str) -> dict[str, Path]:
        return {
            name(project, theme): build(project, theme)
            for other, theme in SITES
            if other == project
        }

    projects = list(dict.fromkeys(project for project, _ in SITES))

    with ThreadPoolExecutor(jobs) as pool:
        results = pool.map(project_sites, projects)

    return {site: path for sites in results for site, path in sites.items()}


def publish(target: Path) -> None:
    """Builds every site and copies the documents shown by the documentation to
    `<target>/<site>/<document>`."""

    for site, path in build_all().items():
        for document in documents(site):
            destination = target / site / document

            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path / document, destination)


def preview(document: Path, page: int, output: Path) -> None:
    """Renders a page of a PDF document to a WebP image."""

    from PIL import Image

    if page < 0:
        page += len(PdfReader(document).pages) + 1

    with tempfile.TemporaryDirectory() as directory:
        image = Path(directory) / "page"
        subprocess.run(  # noqa: S603
            [
                *("pdftoppm", "-png", "-r", str(RESOLUTION)),
                *("-f", str(page), "-l", str(page), "-singlefile"),
                *(str(document), str(image)),
            ],
            check=True,
        )
        Image.open(image.with_suffix(".png")).save(output, quality=85, method=6)


def main() -> None:
    """Builds every site and renders the previews."""

    if shutil.which("pdftoppm") is None:
        sys.exit("pdftoppm is required to render previews (it is part of Poppler).")

    try:
        sites = build_all()
    except BuildError as error:
        sys.exit(str(error))

    IMAGES.mkdir(parents=True, exist_ok=True)

    for image in IMAGES.glob("*.webp"):
        image.unlink()

    for site, path in sites.items():
        for index, (document, page, _) in enumerate(PREVIEWS.get(site, []), 1):
            preview(path / document, page, IMAGES / f"{site}-{index}.webp")

        print(f"Built {site}")


if __name__ == "__main__":
    main()
