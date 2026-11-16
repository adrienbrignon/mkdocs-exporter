import asyncio
from types import SimpleNamespace
from typing import Any

from playwright.async_api import Error as PlaywrightError

from mkdocs_exporter.core.browser import Diagnostics, _Watch

ORIGIN = "127.0.0.1:8000"


def test_errors_are_sorted_by_the_phase_they_occurred_in() -> None:
    diagnostics = Diagnostics()

    diagnostics.record(
        [
            {"phase": "hook", "message": "in a hook"},
            {"phase": "loading", "message": "while loading"},
            {"phase": "rendering", "message": "while rendering"},
            {"phase": "printing", "message": "once ready"},
        ]
    )

    assert diagnostics.hook_errors == ["in a hook"]
    assert diagnostics.errors == ["while loading", "while rendering"]
    assert diagnostics.late_errors == ["once ready"]
    assert not diagnostics.complete


def test_summaries_are_limited() -> None:
    diagnostics = Diagnostics(failed_requests=[f"/{index}.png" for index in range(7)])

    assert diagnostics.summary(limit=5).splitlines() == [
        "Failed requests:",
        *(f"  - /{index}.png" for index in range(5)),
        "  - ... and 2 more",
    ]


def test_requests_failing_on_the_website_are_resources_of_the_page() -> None:
    watch = _Watch(ORIGIN, debug=False)

    watch._request_failed(
        SimpleNamespace(url=f"http://{ORIGIN}/a.css", failure="net::ERR_ABORTED")
    )
    watch._request_failed(
        SimpleNamespace(url="https://cdn.example.org/b.js", failure="net::ERR_FAILED")
    )

    assert watch.resources == {f"http://{ORIGIN}/a.css"}
    assert watch.diagnostics.failed_requests == [
        f"http://{ORIGIN}/a.css (net::ERR_ABORTED)"
    ]
    assert watch.diagnostics.external_failed_requests == [
        "https://cdn.example.org/b.js (net::ERR_FAILED)"
    ]


def test_responses_with_errors_are_failed_requests() -> None:
    watch = _Watch(ORIGIN, debug=False)

    watch._response(SimpleNamespace(url=f"http://{ORIGIN}/a.png", status=200))
    watch._response(SimpleNamespace(url=f"http://{ORIGIN}/b.png", status=404))
    watch._response(SimpleNamespace(url="https://example.org/c.png", status=500))

    assert watch.resources == {f"http://{ORIGIN}/a.png", f"http://{ORIGIN}/b.png"}
    assert watch.diagnostics.failed_requests == [f"http://{ORIGIN}/b.png (HTTP 404)"]


def test_console_errors_are_recorded_and_messages_logged_in_debug_mode(
    caplog: Any,
) -> None:
    caplog.set_level("INFO", logger="mkdocs")
    watch = _Watch(ORIGIN, debug=True)

    watch._console(SimpleNamespace(type="error", text="Oops"))
    watch._console(SimpleNamespace(type="log", text="Hello"))

    assert watch.diagnostics.console == ["Oops"]
    assert "[mkdocs-exporter.pdf.browser] (log) Hello" in caplog.text


def test_errors_of_closed_pages_are_not_collected() -> None:
    class Closed:
        async def evaluate(self, script: str) -> Any:
            raise PlaywrightError("Target page, context or browser has been closed")

    watch = _Watch(ORIGIN, debug=False)

    asyncio.run(watch.collect(Closed()))

    assert watch.diagnostics == Diagnostics()
