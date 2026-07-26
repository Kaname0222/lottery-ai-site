import asyncio
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")


class RateLimiter:
    """基于 asyncio.Semaphore 的简易并发限流器。"""

    def __init__(self, max_concurrent: int = 3):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def run(self, coro: Awaitable[T]) -> T:
        async with self.semaphore:
            return await coro

    async def gather(self, coros: list[Awaitable[T]]) -> list[T]:
        return await asyncio.gather(*[self.run(c) for c in coros])
