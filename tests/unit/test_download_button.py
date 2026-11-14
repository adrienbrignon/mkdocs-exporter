"""Tests of the download button's helpers."""

from types import SimpleNamespace

import pytest

from mkdocs_exporter.formats.pdf.buttons import download


def page(
    url: str, pdf: str | None, title: str = "Intro", **meta: str
) -> SimpleNamespace:
    """A minimal stand-in for a MkDocs page."""

    formats = {"pdf": {"url": pdf}} if pdf else {}

    return SimpleNamespace(url=url, title=title, meta=meta, formats=formats)


@pytest.mark.parametrize(
    ("url", "pdf", "expected"),
    [
        ("", "index.pdf", "index.pdf"),
        ("guide/intro/", "guide/intro/index.pdf", "index.pdf"),
        pytest.param(
            "index.html",
            "index.pdf",
            "index.pdf",
            marks=pytest.mark.xfail(reason="#60: one '../' too many"),
        ),
        pytest.param(
            "guide/intro.html",
            "guide/intro.pdf",
            "intro.pdf",
            marks=pytest.mark.xfail(reason="#60: one '../' too many"),
        ),
    ],
)
def test_href_is_relative_to_the_page(url: str, pdf: str, expected: str) -> None:
    assert download.href(page(url, pdf)) == expected


def test_enabled_only_when_a_pdf_is_generated() -> None:
    assert download.enabled(page("", "index.pdf")) is True
    assert download.enabled(page("", None)) is False


def test_download_file_name_uses_the_page_title() -> None:
    assert download.download(page("", "index.pdf", title="Getting started")) == (
        "Getting started.pdf"
    )


def test_icon_can_be_overridden_by_the_page() -> None:
    assert download.icon(page("", "index.pdf")) == "material-file-download-outline"
    assert download.icon(page("", "index.pdf", **{"pdf-icon": "custom"})) == "custom"
