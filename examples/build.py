"""Builds the example projects and renders the previews shown by the documentation.

Run it with `make examples`: it needs `pdftoppm` (from Poppler) and Pillow (a dependency of
the documentation) to render previews.

Every folder holding a `mkdocs.yml` file is an example project, built into
`.cache/examples/<project>` (warnings fail the build). The documents linked from the
README are copied to this folder, and the pages listed in `PREVIEWS` are rendered to
`docs/assets/images/examples/<project>-<n>.webp`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / ".cache" / "examples"
IMAGES = ROOT.parent / "docs" / "assets" / "images" / "examples"

PREVIEWS: dict[str, list[tuple[str, int]]] = {
    "field-guide": [
        ("field-guide.pdf", 1),
        ("field-guide.pdf", 2),
        ("field-guide.pdf", 4),
        ("guide/writing/index.pdf", 3),
        ("guide/writing/index.pdf", 1),
        ("field-guide.pdf", -1),
    ],
    "field-guide-readthedocs": [("guide/writing/index.pdf", 3)],
    "page-numbers": [("guide/writing/index.pdf", 1)],
    "cover-pages": [("guide/writing/index.pdf", 1), ("guide/writing/index.pdf", 2)],
    "book": [
        ("field-guide.pdf", 1),
        ("field-guide.pdf", 2),
        ("field-guide.pdf", 8),
        ("field-guide.pdf", 9),
    ],
    "page-layout": [
        ("reference/paper-sizes/index.pdf", 1),
        ("reference/paper-sizes/index.pdf", 2),
    ],
    "print-styles": [("reference/glossary/index.pdf", 1)],
    "documents": [("pdf/field-guide.pdf", 1)],
    "toc-template": [("field-guide.pdf", 1)],
}
"""The pages shown by the documentation, by site: (document, page number, < 0 from the end)."""

RESOLUTION = 72
"""The resolution of previews (dots per inch)."""


SITES = [
    *((path.parent.name, None) for path in sorted(ROOT.glob("*/mkdocs.yml"))),
    ("field-guide", "readthedocs"),
]
"""The sites to build: (project, theme replacing the project's)."""


def name(project: str, theme: str | None) -> str:
    """The name of a site."""

    return f"{project}-{theme}" if theme else project


def build(project: str, theme: str | None = None) -> Path:
    """Builds a project, returning its site directory."""

    site = OUTPUT / name(project, theme)
    command = [
        *(sys.executable, "-m", "mkdocs", "build", "--strict"),
        *("--config-file", str(ROOT / project / "mkdocs.yml")),
        *("--site-dir", str(site)),
        *(("--theme", theme) if theme else ()),
    ]

    print(f"Building {name(project, theme)}...", flush=True)
    result = subprocess.run(command, capture_output=True, text=True)  # noqa: S603

    if result.returncode:
        sys.exit(f"Failed to build {name(project, theme)}:\n{result.stderr}")

    return site


def preview(document: Path, page: int, output: Path) -> None:
    """Renders a page of a PDF document to a WebP image."""

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
    """Builds every example project."""

    if shutil.which("pdftoppm") is None:
        sys.exit("pdftoppm is required to render previews (it is part of Poppler).")

    IMAGES.mkdir(parents=True, exist_ok=True)

    for image in IMAGES.glob("*.webp"):
        image.unlink()

    for project, theme in SITES:
        site = build(project, theme)

        for index, (document, page) in enumerate(
            PREVIEWS.get(name(project, theme), []), 1
        ):
            preview(
                site / document, page, IMAGES / f"{name(project, theme)}-{index}.webp"
            )

    site = OUTPUT / "field-guide"

    shutil.copy(site / "field-guide.pdf", ROOT / "field-guide.pdf")
    shutil.copy(site / "guide/writing/index.pdf", ROOT / "themes" / "material.pdf")
    shutil.copy(
        OUTPUT / "field-guide-readthedocs" / "guide/writing/index.pdf",
        ROOT / "themes" / "readthedocs.pdf",
    )


if __name__ == "__main__":
    main()
