import random
import asyncio

async def sleep_backoff(attempt: int, base: float = 0.25, cap: float = 3.0):
    delay = min(base * (2 ** attempt) + random.random() * 0.05, cap)
    await asyncio.sleep(delay)
