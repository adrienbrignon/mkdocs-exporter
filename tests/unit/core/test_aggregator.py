"""Tests of the aggregation logic."""

from typing import Any

import pytest

from mkdocs_exporter.core.aggregator import (
    Measure,
    kept_covers,
    metadata,
    plan,
    running_heads,
)


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


def test_metadata_keys_are_normalized() -> None:
    assert metadata({"title": "T", "/Author": "A", "subject": None}) == {
        "/Title": "T",
        "/Author": "A",
    }


def measure(*parts: dict[str, Any], **values: Any) -> Measure:
    """A measured book (pages of parts as `span`, 0-based)."""

    return Measure.parse(
        {
            "pages": values.pop("pages", max(p["span"][1] for p in parts) + 1),
            "parts": [{"headings": [], **part} for part in parts],
            **values,
        }
    )


def heading(level: int, title: str, page: int, top: float = 0) -> dict[str, Any]:
    return {
        "level": level,
        "title": title,
        "id": title.lower(),
        "page": page,
        "top": top,
    }


def test_measures_must_be_complete() -> None:
    with pytest.raises(ValueError, match="could not be measured"):
        Measure.parse({"error": "boom"})


def test_odd_starts_insert_blank_pages() -> None:
    book = measure(
        {"id": "a", "span": [0, 2]},
        {"id": "b", "span": [3, 4]},
        {"id": "c", "span": [5, 5]},
    )

    result = plan(book, "odd")

    assert result.blanks == ["b"]
    assert result.shifts == {"a": 0, "b": 1, "c": 1}
    assert result.pages == 7
    assert plan(book).blanks == []


def test_blank_pages_already_printed_are_planned_again() -> None:
    book = measure(
        {"id": "a", "span": [0, 2]},
        {"id": "b", "span": [4, 5]},
        {"id": "c", "span": [6, 6]},
        blanks=[[3, 3]],
    )

    result = plan(book, "odd")

    assert result.blanks == ["b"]
    assert result.shifts == {"a": 0, "b": 0, "c": 0}
    assert result.pages == 7


def test_content_leaves_covers_and_the_table_of_contents_out() -> None:
    book = measure(
        {"id": "a", "span": [0, 4], "front": [0, 0], "back": [4, 4]},
        toc=[1, 1],
    )

    assert list(book.content(book.parts[0])) == [2, 3]
    assert book.anchors()["a"].page == 2


def test_running_heads_start_over_in_each_part() -> None:
    book = measure(
        {
            "id": "a",
            "span": [0, 3],
            "front": [0, 0],
            "headings": [heading(1, "A", 1), heading(2, "A1", 1), heading(3, "x", 2)],
        },
        {"id": "b", "span": [4, 5], "headings": [heading(1, "B", 5)]},
    )

    assert running_heads(book, plan(book)) == ["", "A", "A1", "A1", "", "B"]


def test_running_heads_follow_blank_pages() -> None:
    book = measure(
        {"id": "a", "span": [0, 0], "headings": [heading(1, "A", 0)]},
        {"id": "b", "span": [1, 1], "headings": [heading(1, "B", 1)]},
    )

    assert running_heads(book, plan(book, "odd")) == ["A", "", "B"]
