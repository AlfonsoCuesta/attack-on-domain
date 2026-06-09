from contextvars import ContextVar

_CommitContext: ContextVar[bool] = ContextVar("_CommitContext", default=False)
