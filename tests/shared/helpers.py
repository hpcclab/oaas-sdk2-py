import asyncio
from typing import Awaitable, Callable, Optional


async def wait_for(predicate: Callable[[], Awaitable[bool]] | Callable[[], bool], timeout: float = 3.0, interval: float = 0.05) -> bool:
    """Wait until predicate returns True or timeout.

    - Supports sync or async predicate
    - Returns True if predicate met before timeout; else False
    """
    end = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end:
        result = predicate()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return True
        await asyncio.sleep(interval)
    return False


async def assert_eventually(predicate: Callable[[], Awaitable[bool]] | Callable[[], bool],
                            timeout: float = 3.0, interval: float = 0.05,
                            message: Optional[str] = None) -> None:
    """Assert that predicate becomes True within timeout.

    Raises AssertionError on timeout.
    """
    ok = await wait_for(predicate, timeout=timeout, interval=interval)
    if not ok:
        raise AssertionError(message or f"Condition not met within {timeout}s")
