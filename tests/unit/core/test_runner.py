import asyncio
import threading

from mkdocs_exporter.core.runner import Loop, run


async def current_thread() -> str:
    await asyncio.sleep(0)

    return threading.current_thread().name


def test_runs_in_the_calling_thread_without_a_running_loop() -> None:
    assert run(current_thread) == threading.current_thread().name


def test_runs_in_another_thread_inside_a_running_loop() -> None:
    async def main() -> str:
        return run(current_thread)

    assert asyncio.run(main()).startswith("mkdocs-exporter")


def test_loop_keeps_its_event_loop_until_closed() -> None:
    loop = Loop()

    async def current_loop() -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    try:
        first, second = loop.run(current_loop), loop.run(current_loop)

        assert first is second
        assert loop.run(current_thread) == "mkdocs-exporter"
    finally:
        loop.close()

    assert first.is_closed()
    assert not any(t.name == "mkdocs-exporter" for t in threading.enumerate())


def test_closing_an_unused_loop() -> None:
    Loop().close()
