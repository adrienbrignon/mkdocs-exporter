import logging

import pytest

from mkdocs_exporter.logging import Logger


def test_messages_are_prefixed_with_their_area(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="mkdocs")

    Logger().info("Started %s", "now")
    Logger("pdf").warning("Rendering '%s'", "index.md")

    assert [record.getMessage() for record in caplog.records] == [
        "[mkdocs-exporter] Started now",
        "[mkdocs-exporter.pdf] Rendering 'index.md'",
    ]
    assert {record.name for record in caplog.records} == {
        "mkdocs.plugins.mkdocs_exporter"
    }
