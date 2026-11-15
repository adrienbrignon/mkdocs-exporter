from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import importlib.metadata
import importlib.resources
import json
import os
import tempfile
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

from mkdocs_exporter.core.browser import Diagnostics, PrintResult
from mkdocs_exporter.core.document import Heading, Layout, Position
from mkdocs_exporter.logging import Logger

logger = Logger("pdf")

FORMAT = 1
"""The version of the cache's format (entries of other versions are ignored)."""

Assets = dict[str, str | None]
"""The fingerprint of the resources a document loaded, by URL (`None` when missing)."""


def fingerprint(*parts: Any) -> str:
    """A fingerprint of some JSON-serializable values."""

    data = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=False)

    return hashlib.sha256(data.encode("utf-8", errors="surrogatepass")).hexdigest()


def digest(data: bytes | None) -> str | None:
    """The fingerprint of a resource (`None` when it's missing)."""

    return None if data is None else hashlib.sha256(data).hexdigest()


@cache
def environment() -> str:
    """A fingerprint of this package: its version and its bundled resources.

    Resources are included so that changes are noticed even when the version isn't
    bumped (development installs).
    """

    try:
        version = importlib.metadata.version("mkdocs-exporter")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        version = "unknown"

    from mkdocs_exporter.core import resources

    contents = []
    pending = [importlib.resources.files(resources)]

    while pending:
        for entry in sorted(pending.pop().iterdir(), key=lambda e: e.name):
            if entry.is_dir():
                pending.append(entry)
            elif not entry.name.endswith((".py", ".pyc")):
                contents.append((entry.name, digest(entry.read_bytes())))

    return fingerprint(FORMAT, version, contents)


class Cache:
    """Printed documents stored in a directory, by key.

    An entry is reused only while the resources the document loaded from the website
    (stylesheets, scripts, images...) are unchanged; resources from other websites are
    assumed not to change.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.used: set[str] = set()

    def get(self, key: str, fresh: Callable[[Assets], bool]) -> PrintResult | None:
        """The document stored for a key, if its resources are `fresh`."""

        metadata = self.directory / f"{key}.json"

        try:
            entry = json.loads(metadata.read_text(encoding="utf-8"))

            if entry.get("format") != FORMAT or not fresh(entry["assets"]):
                return None

            result = PrintResult(
                pdf=(self.directory / f"{key}.pdf").read_bytes(),
                diagnostics=Diagnostics(**entry["diagnostics"]),
                layout=_layout(entry["layout"]) if entry["layout"] else None,
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

        self.used.add(key)

        return result

    def put(self, key: str, result: PrintResult, assets: Assets) -> None:
        """Stores a document (failures are logged, never raised)."""

        entry = {
            "format": FORMAT,
            "assets": assets,
            "diagnostics": dataclasses.asdict(result.diagnostics),
            "layout": dataclasses.asdict(result.layout) if result.layout else None,
        }

        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            # The metadata is written last: an entry without it is never read.
            _write(self.directory / f"{key}.pdf", result.pdf)
            _write(
                self.directory / f"{key}.json",
                json.dumps(entry, ensure_ascii=False).encode("utf-8"),
            )
        except OSError as error:
            logger.warning("Failed to write to the cache: %s", error)
            return

        self.used.add(key)

    def prune(self) -> None:
        """Removes the entries that were neither read nor written since created."""

        if not self.directory.is_dir():
            return

        for file in self.directory.iterdir():
            stale = file.suffix in (".json", ".pdf") and file.stem not in self.used

            if stale or file.name.startswith(".tmp-"):
                with contextlib.suppress(OSError):
                    file.unlink()


def _write(path: Path, data: bytes) -> None:
    """Writes a file atomically."""

    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")

    try:
        with os.fdopen(fd, "wb") as file:
            file.write(data)

        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def _layout(data: dict[str, Any]) -> Layout:
    """A layout read from the cache."""

    return Layout(
        pages=data["pages"],
        headings=[
            Heading(
                level=heading["level"],
                title=heading["title"],
                id=heading["id"],
                position=Position(**heading["position"]),
            )
            for heading in data["headings"]
        ],
        anchors={key: Position(**value) for key, value in data["anchors"].items()},
    )
