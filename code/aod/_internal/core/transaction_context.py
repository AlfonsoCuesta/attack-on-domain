from contextvars import ContextVar


_active_transaction: ContextVar[object | None] = ContextVar(
    "_active_transaction", default=None
)


def get_active_transaction() -> object | None:
    return _active_transaction.get()
