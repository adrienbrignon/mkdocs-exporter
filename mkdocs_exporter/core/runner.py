"""Runs coroutines without interfering with the caller's event loop."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")


def run(factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """Runs a coroutine to completion on an event loop owned by the exporter.

    The global event loop is never touched. When the calling thread already runs an event
    loop (another plugin, a notebook...), the coroutine runs in a dedicated thread.
    """

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        with asyncio.Runner() as runner:
            return runner.run(factory())

    with ThreadPoolExecutor(1, thread_name_prefix="mkdocs-exporter") as executor:
        return executor.submit(_run, factory).result()


def _run(factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    with asyncio.Runner() as runner:
        return runner.run(factory())


class Loop:
    """An event loop running in a dedicated thread until closed.

    Objects bound to an event loop (such as a launched browser) can be kept from one run
    to the next, e.g. across the rebuilds of `mkdocs serve`.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def run(self, factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        """Runs a coroutine to completion on the loop, starting it if needed."""

        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._loop.run_forever, name="mkdocs-exporter", daemon=True
            )
            self._thread.start()

        return asyncio.run_coroutine_threadsafe(factory(), self._loop).result()

    def close(self) -> None:
        """Stops the loop and its thread."""

        loop, thread = self._loop, self._thread

        if loop is None or thread is None:
            return

        self._loop = self._thread = None

        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()
