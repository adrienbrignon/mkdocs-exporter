"""Runs coroutines without interfering with the caller's event loop."""

from __future__ import annotations

import asyncio
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
