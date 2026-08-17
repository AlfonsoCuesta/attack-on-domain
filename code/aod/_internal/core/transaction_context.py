from contextvars import ContextVar
from typing import Protocol


class TransactionContext(Protocol):
    def register_session(self, session: object) -> None: ...


_active_transaction: ContextVar[TransactionContext | None] = ContextVar(
    "_active_transaction", default=None
)


def get_active_transaction() -> TransactionContext | None:
    return _active_transaction.get()
