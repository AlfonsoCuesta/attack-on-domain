from __future__ import annotations

from inspect import iscoroutine
from typing import Any


async def should_await(value: Any) -> Any:
    if iscoroutine(value):
        return await value
    return value
