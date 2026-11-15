"""Tests of the aggregation logic."""

import pytest

from mkdocs_exporter.core.aggregator import (
    kept_covers,
    metadata,
    plan,
    renumber,
    total_pages,
)
from mkdocs_exporter.core.document import Document, Layout


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("all", ["bf", "bf", "bf"]),
        ("none", ["", "", ""]),
        ("front", ["f", "f", "f"]),
        ("back", ["b", "b", "b"]),
        ("limits", ["f", "", "b"]),
        ("book", ["f", "f", "bf"]),
    ],
)
def test_kept_covers(mode: str, expected: list[str]) -> None:
    kept = ["".join(sorted(c[0] for c in kept_covers(mode, i, 3))) for i in range(3)]

    assert kept == expected


@pytest.mark.parametrize("mode", ["limits", "book"])
def test_a_single_document_keeps_its_covers(mode: str) -> None:
    assert kept_covers(mode, 0, 1) == {"front", "back"}


def test_plan_ignores_covers_a_document_does_not_have() -> None:
    documents = [Document(id="a", url="", path="", covers=[])]

    parts = plan(documents, {"a": Layout(pages=2)}, "all")

    assert parts[0].covers == set()
    assert parts[0].pages == 2


def test_metadata_keys_are_normalized() -> None:
    assert metadata({"title": "T", "/Author": "A", "subject": None}) == {
        "/Title": "T",
        "/Author": "A",
    }


def test_renumber_uses_actual_page_counts() -> None:
    documents = [Document(id=name, url="", path="", covers=[]) for name in "ab"]
    parts = plan(documents, {"a": Layout(pages=3), "b": Layout(pages=2)}, "all")

    parts = renumber(parts, [Layout(pages=2), Layout(pages=4)])

    assert [(p.first_page, p.pages) for p in parts] == [(1, 2), (3, 4)]


def test_odd_starts_insert_blank_pages() -> None:
    documents = [Document(id=name, url="", path="", covers=[]) for name in "abc"]
    layouts = {"a": Layout(pages=3), "b": Layout(pages=2), "c": Layout(pages=1)}

    parts = plan(documents, layouts, "all", start="odd")

    assert [(p.first_page, p.blank_before) for p in parts] == [
        (1, False),
        (5, True),
        (7, False),
    ]
    assert total_pages(parts) == 7
