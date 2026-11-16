import importlib.resources
from pathlib import Path

import pytest

from mkdocs_exporter.core.browser import Diagnostics, PrintResult
from mkdocs_exporter.core.cache import Cache, digest, environment, fingerprint
from mkdocs_exporter.core.document import Heading, Layout, Position


def result() -> PrintResult:
    position = Position(page=1, top=12.5)

    return PrintResult(
        pdf=b"%PDF-1.7 document",
        diagnostics=Diagnostics(errors=["an error"]),
        layout=Layout(
            pages=2,
            headings=[Heading(level=2, title="Title", id="title", position=position)],
            anchors={"title": position},
        ),
    )


def test_fingerprints() -> None:
    assert fingerprint("a", {"b": 1, "c": 2}) == fingerprint("a", {"c": 2, "b": 1})
    assert fingerprint("a") != fingerprint("b")
    assert digest(None) is None
    assert digest(b"x") != digest(b"y")
    assert environment() == environment()


def test_bytecode_is_not_part_of_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Other processes write bytecode while the package's resources are read (e.g.
    `__init__.cpython-314.pyc.<random>`, renamed once written)."""

    (tmp_path / "base.css").write_text("body {}")
    (tmp_path / "__pycache__").mkdir()
    temporary = tmp_path / "__pycache__" / "__init__.cpython-314.pyc.124250667743552"
    temporary.write_bytes(b"bytecode being written")
    monkeypatch.setattr(importlib.resources, "files", lambda package: tmp_path)

    fingerprint = environment.__wrapped__()
    temporary.unlink()

    assert environment.__wrapped__() == fingerprint


def test_entries_are_read_back(tmp_path: Path) -> None:
    cache = Cache(tmp_path / "cache")

    cache.put("key", result(), {"/style.css": "abc"})

    assert Cache(tmp_path / "cache").get("key", lambda assets: True) == result()


def test_entries_with_changed_resources_are_not_reused(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    seen = []

    cache.put("key", result(), {"/style.css": "abc", "/missing.png": None})

    def fresh(assets: dict[str, str | None]) -> bool:
        seen.append(assets)
        return False

    assert cache.get("key", fresh) is None
    assert seen == [{"/style.css": "abc", "/missing.png": None}]


def test_unreadable_entries_are_ignored(tmp_path: Path) -> None:
    cache = Cache(tmp_path)

    assert cache.get("missing", lambda assets: True) is None

    (tmp_path / "corrupted.json").write_text("{", encoding="utf-8")
    (tmp_path / "old.json").write_text('{"format": 0}', encoding="utf-8")
    cache.put("orphan", result(), {})
    (tmp_path / "orphan.pdf").unlink()

    assert cache.get("corrupted", lambda assets: True) is None
    assert cache.get("old", lambda assets: True) is None
    assert cache.get("orphan", lambda assets: True) is None


def test_unused_entries_are_pruned(tmp_path: Path) -> None:
    Cache(tmp_path).put("old", result(), {})
    Cache(tmp_path).put("kept", result(), {})
    (tmp_path / ".tmp-leftover").write_bytes(b"")

    cache = Cache(tmp_path)

    assert cache.get("kept", lambda assets: True) is not None

    cache.put("new", result(), {})
    cache.prune()

    assert sorted(file.name for file in tmp_path.iterdir()) == [
        "kept.json",
        "kept.pdf",
        "new.json",
        "new.pdf",
    ]


def test_write_failures_are_not_fatal(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("", encoding="utf-8")
    cache = Cache(tmp_path / "file" / "cache")

    cache.put("key", result(), {})

    assert cache.get("key", lambda assets: True) is None
