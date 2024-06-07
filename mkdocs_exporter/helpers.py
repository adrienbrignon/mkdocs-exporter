import asyncio

from typing import Coroutine, Sequence
from collections import UserDict


def resolve(object, *args, **kwargs):
  """Resolves a callable."""

  if callable(object):
    return resolve(object(*args, **kwargs), *args, **kwargs)
  if isinstance(object, list):
    return [resolve(v, *args, **kwargs) for v in object]
  if isinstance(object, (dict, UserDict)):
    return {k: resolve(v, *args, **kwargs) for k, v in object.items()}

  return object


def concurrently(coroutines: Sequence[Coroutine], concurrency: int) -> Sequence[Coroutine]:
  """Runs coroutines concurrently."""

  semaphore = asyncio.Semaphore(concurrency)

  async def limit(coroutine: Coroutine) -> Coroutine:
    async with semaphore:
      coroutines.remove(coroutine)

      return await asyncio.create_task(coroutine)

  return [limit(coroutine) for coroutine in coroutines]
