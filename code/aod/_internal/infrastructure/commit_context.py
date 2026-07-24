from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_CommitContext: ContextVar[bool] = ContextVar("_CommitContext", default=False)


@contextmanager
def commit_context() -> Iterator[None]:
    token = _CommitContext.set(True)
    try:
        yield
    finally:
        _CommitContext.reset(token)
