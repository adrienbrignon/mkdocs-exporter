"""The headless browser that prints pages to PDF."""

from __future__ import annotations

import contextlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any
from urllib.parse import urlsplit

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import (
    BrowserContext,
    ConsoleMessage,
    Playwright,
    Request,
    async_playwright,
)
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from mkdocs_exporter.core.document import Layout
from mkdocs_exporter.logging import logger

ARGUMENTS = (
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--font-render-hinting=none",
)
"""Arguments always passed to the browser."""


@dataclass
class Diagnostics:
    """What went wrong (or looked suspicious) while rendering a page."""

    hook_errors: list[str] = field(default_factory=list)
    """Errors thrown by the `window.MkDocsExporter` hooks."""

    errors: list[str] = field(default_factory=list)
    """Uncaught errors of the page's scripts, raised before pagination.

    They usually occur on the website too and rarely affect the document.
    """

    late_errors: list[str] = field(default_factory=list)
    """Uncaught errors of the page's scripts, raised while paginating or printing.

    They usually come from the website's scripts reacting to the elements Paged.js moves
    around, and don't affect the document.
    """

    console: list[str] = field(default_factory=list)
    """Messages logged to the console as errors."""

    failed_requests: list[str] = field(default_factory=list)
    """Requests to the website itself that failed (missing files, typically)."""

    external_failed_requests: list[str] = field(default_factory=list)
    """Requests to other websites that failed."""

    def summary(self, limit: int = 5) -> str:
        """A human-readable summary."""

        lines = []

        for title, items in (
            ("Errors in hooks", self.hook_errors),
            ("JavaScript errors", self.errors),
            ("Console errors", self.console),
            ("Failed requests", self.failed_requests),
            ("Failed external requests", self.external_failed_requests),
        ):
            if items:
                lines.append(f"{title}:")
                lines.extend(f"  - {item}" for item in items[:limit])

                if len(items) > limit:
                    lines.append(f"  - ... and {len(items) - limit} more")

        return "\n".join(lines)


@dataclass
class PrintResult:
    """A page printed to PDF."""

    pdf: bytes
    layout: Layout
    diagnostics: Diagnostics


class RenderError(Exception):
    """A page could not be printed."""

    def __init__(self, message: str, diagnostics: Diagnostics) -> None:
        super().__init__(message)

        self.message = message
        self.diagnostics = diagnostics

    def __str__(self) -> str:
        summary = self.diagnostics.summary()

        return f"{self.message}\n{summary}" if summary else self.message


class Browser:
    """A headless Chromium driven by Playwright."""

    def __init__(
        self,
        *,
        headless: bool = True,
        timeout: int = 60_000,
        args: Sequence[str] = (),
        channel: str | None = None,
        debug: bool = False,
    ) -> None:
        self.headless = headless
        self.timeout = timeout
        self.args = [*ARGUMENTS, *args]
        self.channel = channel
        self.debug = debug
        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> Browser:
        logger.info("[mkdocs-exporter.pdf] Launching browser...")

        self._playwright = await async_playwright().start()

        try:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless, args=self.args, channel=self.channel
            )
            self._context = await self._browser.new_context()
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for close in (
            self._context.close if self._context else None,
            self._browser.close if self._browser else None,
            self._playwright.stop if self._playwright else None,
        ):
            if close is not None:
                with contextlib.suppress(PlaywrightError):
                    await close()

        self._context = self._browser = self._playwright = None

    async def print(
        self, url: str, *, outline: bool = True, tagged: bool = True
    ) -> PrintResult:
        """Opens a page, waits for it to be paginated and prints it to PDF."""

        if self._context is None:
            raise RuntimeError("The browser has not been launched")

        origin = urlsplit(url).netloc
        diagnostics = Diagnostics()
        page = await self._context.new_page()

        def on_console(message: ConsoleMessage) -> None:
            if self.debug:
                logger.info(
                    "[mkdocs-exporter.pdf.browser] (%s) %s", message.type, message.text
                )
            if message.type == "error":
                diagnostics.console.append(message.text)

        def on_request_failed(request: Request) -> None:
            failure = f"{request.url} ({request.failure})"
            target = (
                diagnostics.failed_requests
                if urlsplit(request.url).netloc == origin
                else diagnostics.external_failed_requests
            )

            target.append(failure)

        def on_response(response: Any) -> None:
            if response.status >= 400 and urlsplit(response.url).netloc == origin:
                diagnostics.failed_requests.append(
                    f"{response.url} (HTTP {response.status})"
                )

        page.on("console", on_console)
        page.on("requestfailed", on_request_failed)
        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="load", timeout=self.timeout)

            state = await page.wait_for_function(
                "() => document.body && document.body.getAttribute('mkdocs-exporter')",
                timeout=self.timeout,
            )

            await self._collect_errors(page, diagnostics)

            if await state.json_value() == "error":
                reason = await page.evaluate("() => window.__MKDOCS_EXPORTER_ERROR__")

                raise RenderError(f"Pagination failed: {reason}", diagnostics)

            result = await page.evaluate("() => window.__MKDOCS_EXPORTER_RESULT__")
            pdf = await page.pdf(
                prefer_css_page_size=True,
                print_background=True,
                outline=outline,
                tagged=tagged,
            )

            await self._collect_errors(page, diagnostics)
        except PlaywrightTimeoutError as error:
            await self._collect_errors(page, diagnostics)

            raise RenderError(
                f"Timed out after {self.timeout} ms waiting for the page to be paginated",
                diagnostics,
            ) from error
        except PlaywrightError as error:
            raise RenderError(f"Browser error: {error.message}", diagnostics) from error
        finally:
            await page.close()

        layout = Layout.parse(result)

        return PrintResult(pdf=pdf, layout=layout, diagnostics=diagnostics)

    @staticmethod
    async def _collect_errors(page: Any, diagnostics: Diagnostics) -> None:
        """Collects the errors recorded by the page since the last collection."""

        try:
            errors = await page.evaluate(
                "() => (window.__MKDOCS_EXPORTER_ERRORS__ || []).splice(0)"
            )
        except PlaywrightError:
            return

        for error in errors or []:
            phase = error.get("phase")
            target = {
                "hook": diagnostics.hook_errors,
                "loading": diagnostics.errors,
                "rendering": diagnostics.errors,
            }.get(phase, diagnostics.late_errors)

            target.append(str(error.get("message")))
