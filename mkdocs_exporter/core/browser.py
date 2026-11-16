from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any
from urllib.parse import urlsplit

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import (
    BrowserContext,
    ConsoleMessage,
    Page,
    Playwright,
    Request,
    Response,
    async_playwright,
)
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from mkdocs_exporter.core.document import Layout
from mkdocs_exporter.logging import Logger

logger = Logger("pdf")
console_logger = Logger("pdf.browser")

READY = """() => window.__MKDOCS_EXPORTER_READY__.then((state) => ({
  state,
  reason: window.__MKDOCS_EXPORTER_ERROR__ || null,
  errors: window.__MKDOCS_EXPORTER_ERRORS__.splice(0),
}))"""
"""Waits for the page to be ready to print (see `pdf.js`)."""

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
    """Uncaught errors of the page's scripts, raised once the page was ready to print.

    They don't affect the document.
    """

    console: list[str] = field(default_factory=list)
    """Messages logged to the console as errors."""

    failed_requests: list[str] = field(default_factory=list)
    """Requests to the website itself that failed (missing files, typically)."""

    external_failed_requests: list[str] = field(default_factory=list)
    """Requests to other websites that failed."""

    def record(self, errors: Sequence[Mapping[str, Any]]) -> None:
        """Records the errors recorded by a page, by the phase they occurred in (see
        `pdf.js`)."""

        for error in errors:
            target = {
                "hook": self.hook_errors,
                "loading": self.errors,
                "rendering": self.errors,
            }.get(str(error.get("phase")), self.late_errors)

            target.append(str(error.get("message")))

    @property
    def complete(self) -> bool:
        """Did every hook succeed, and every resource load?"""

        return not (
            self.hook_errors or self.failed_requests or self.external_failed_requests
        )

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
    diagnostics: Diagnostics
    layout: Layout | None = None
    """The layout of the document, when it has been read."""

    resources: set[str] = field(default_factory=set)
    """The URLs requested to the page's origin (besides the page itself)."""

    measure: Any = None
    """What the page measured while it was last printed, if anything (see `Printed`)."""


@dataclass
class Printed:
    """A print of a page, given to `Refine`."""

    pdf: bytes
    """The printed document (only its first page for a draft, see `Browser.print`)."""

    measure: Any = None
    """What the page measured while being printed (`window.__MKDOCS_EXPORTER_LAYOUT__`)."""

    draft: bool = False
    """Was it a draft (only the first page printed)?"""


Refine = Callable[[Printed], Awaitable[str | None]]
"""Computes, from a print, a script adjusting the page before printing it again (or
`None` when the print is final)."""

MEASURE = "() => window.__MKDOCS_EXPORTER_LAYOUT__ || null"
"""Reads what the page measured while it was printed (see `book.js`)."""

ERRORS = "() => (window.__MKDOCS_EXPORTER_ERRORS__ || []).splice(0)"
"""Reads the errors the page recorded since they were last read (see `pdf.js`)."""


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

    @property
    def options(self) -> tuple[bool, tuple[str, ...], str | None]:
        """The options the browser is launched with."""

        return self.headless, tuple(self.args), self.channel

    @property
    def version(self) -> str:
        """The version of the browser."""

        if self._browser is None:
            raise RuntimeError("The browser has not been launched")

        return self._browser.version

    @property
    def running(self) -> bool:
        """Whether the browser has been launched and is still usable."""

        return self._browser is not None and self._browser.is_connected()

    async def launch(self) -> Browser:
        """Launches the browser (closing it first if it was launched)."""

        if self._playwright is not None:
            await self.close()

        logger.info("Launching browser...")

        self._playwright = await async_playwright().start()

        try:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless, args=self.args, channel=self.channel
            )
            self._context = await self._browser.new_context()
        except BaseException:
            await self.close()
            raise

        return self

    async def renew(self) -> None:
        """Starts afresh (new cache, cookies and storage) for the next pages."""

        if self._browser is None or self._context is None:
            raise RuntimeError("The browser has not been launched")

        await self._context.close()

        self._context = await self._browser.new_context()

    async def close(self) -> None:
        """Closes the browser."""

        for close in (
            self._context.close if self._context else None,
            self._browser.close if self._browser else None,
            self._playwright.stop if self._playwright else None,
        ):
            if close is not None:
                with contextlib.suppress(PlaywrightError):
                    await close()

        self._context = self._browser = self._playwright = None

    async def __aenter__(self) -> Browser:
        return await self.launch()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def print(
        self,
        url: str,
        *,
        outline: bool = True,
        tagged: bool = True,
        refine: Refine | None = None,
        draft: bool = False,
        attempts: int = 1,
        measure: bool = False,
    ) -> PrintResult:
        """Opens a page, waits for it to be ready and prints it to PDF.

        When `refine` is given, it receives each print and may return a script adjusting
        the page (e.g. from the position of its elements), which is then printed again,
        up to `attempts` times.

        Args:
            url: The URL of the page.
            outline: Should the browser generate bookmarks (from headings)?
            tagged: Should the document be tagged (accessibility)?
            refine: Adjusts the page from a print (see above).
            draft: Is the first print only meant to be measured? Only its first page is
                then printed: the whole document is still laid out (and measured) for
                a quarter to a third of the cost of a full print. Requires `refine`,
                which can't then read the document of that print.
            attempts: How many times the page may be adjusted and printed again.
            measure: Should what the page measures while printed be read (it always is
                with `refine`)?
        """

        if self._context is None:
            raise RuntimeError("The browser has not been launched")

        watch = _Watch(urlsplit(url).netloc, self.debug)
        diagnostics = watch.diagnostics
        page = await self._context.new_page()
        printer = _Printer(page, outline, tagged, measure or refine is not None)

        watch.attach(page)

        try:
            await self._open(page, url, diagnostics)

            printed = await printer.print(draft=draft and refine is not None)

            if refine is not None:
                printed = await printer.refine(printed, refine, attempts)
            if logger.isEnabledFor(logging.DEBUG):
                # Only logged at the debug level.
                await watch.collect(page)
        except (PlaywrightTimeoutError, TimeoutError) as error:
            await watch.collect(page)

            raise RenderError(
                f"Timed out after {self.timeout} ms waiting for the page to be ready",
                diagnostics,
            ) from error
        except PlaywrightError as error:
            raise RenderError(f"Browser error: {error.message}", diagnostics) from error
        finally:
            await page.close()

        watch.resources.discard(url)

        return PrintResult(
            pdf=printed.pdf,
            diagnostics=diagnostics,
            resources=watch.resources,
            measure=printed.measure,
        )

    async def _open(self, page: Page, url: str, diagnostics: Diagnostics) -> None:
        """Opens a page and waits for it to be ready to print (see `pdf.js`)."""

        await page.goto(url, wait_until="load", timeout=self.timeout)

        state = await asyncio.wait_for(page.evaluate(READY), self.timeout / 1000)

        diagnostics.record(state["errors"])

        if state["state"] == "error":
            raise RenderError(f"Rendering failed: {state['reason']}", diagnostics)


async def relaunch(kept: Browser | None, browser: Browser) -> Browser:
    """The browser of a new build, reusing the one kept from the previous build.

    The kept browser is reused when it's still running and launched with the same
    options: it gets the other options of the new browser and starts afresh (see
    `Browser.renew`). Otherwise, it's closed and the new browser is launched.
    """

    if kept is not None and kept.running and kept.options == browser.options:
        kept.timeout, kept.debug = browser.timeout, browser.debug

        await kept.renew()

        return kept
    if kept is not None:
        await kept.close()

    return await browser.launch()


class _Watch:
    """Records what a page logs and requests."""

    def __init__(self, origin: str, debug: bool) -> None:
        self.origin = origin
        """The origin (host and port) of the website."""
        self.debug = debug
        self.diagnostics = Diagnostics()
        self.resources: set[str] = set()
        """The URLs requested to the website (see `PrintResult.resources`)."""

    def attach(self, page: Page) -> None:
        """Starts recording what a page logs and requests."""

        page.on("console", self._console)
        page.on("requestfailed", self._request_failed)
        page.on("response", self._response)

    async def collect(self, page: Page) -> None:
        """Collects the errors the page recorded since they were last collected."""

        try:
            errors = await page.evaluate(ERRORS)
        except PlaywrightError:
            return

        self.diagnostics.record(errors or [])

    def _console(self, message: ConsoleMessage) -> None:
        if self.debug:
            console_logger.info("(%s) %s", message.type, message.text)
        if message.type == "error":
            self.diagnostics.console.append(message.text)

    def _request_failed(self, request: Request) -> None:
        failure = f"{request.url} ({request.failure})"

        if urlsplit(request.url).netloc == self.origin:
            self.resources.add(request.url)
            self.diagnostics.failed_requests.append(failure)
        else:
            self.diagnostics.external_failed_requests.append(failure)

    def _response(self, response: Response) -> None:
        if urlsplit(response.url).netloc == self.origin:
            self.resources.add(response.url)

            if response.status >= 400:
                self.diagnostics.failed_requests.append(
                    f"{response.url} (HTTP {response.status})"
                )


class _Printer:
    """Prints a page that is ready, adjusting it between prints."""

    def __init__(self, page: Page, outline: bool, tagged: bool, measure: bool) -> None:
        self.page = page
        self.outline = outline
        self.tagged = tagged
        self.measure = measure

    async def print(self, draft: bool = False) -> Printed:
        """Prints the page (only its first page for a draft, untagged and without
        bookmarks), reading what it measured."""

        pdf = await self.page.pdf(
            prefer_css_page_size=True,
            print_background=True,
            outline=self.outline and not draft,
            tagged=self.tagged and not draft,
            page_ranges="1" if draft else "",
        )
        measured = await self.page.evaluate(MEASURE) if self.measure else None

        return Printed(pdf=pdf, measure=measured, draft=draft)

    async def refine(self, printed: Printed, refine: Refine, attempts: int) -> Printed:
        """Adjusts the page from its last print and prints it again, until `refine` has
        nothing to adjust (a draft is always printed again) or up to `attempts` times."""

        for _ in range(attempts):
            script = await refine(printed)

            if script is None and not printed.draft:
                break
            if script:
                await self.page.evaluate(script)

            printed = await self.print()

        return printed
