"""Tests of the coroutine runner."""

import asyncio
import threading

from mkdocs_exporter.core.runner import run


async def current_thread() -> str:
    await asyncio.sleep(0)

    return threading.current_thread().name


def test_runs_in_the_calling_thread_without_a_running_loop() -> None:
    assert run(current_thread) == threading.current_thread().name


def test_runs_in_another_thread_inside_a_running_loop() -> None:
    async def main() -> str:
        return run(current_thread)

    assert asyncio.run(main()).startswith("mkdocs-exporter")
