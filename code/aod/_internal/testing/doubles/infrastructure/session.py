from __future__ import annotations

from typing import Any, TypeVar

from aod._internal.infrastructure.session import AsyncSession, Session
from aod._internal.testing.doubles.stubs import _make_generic_stub

TSession = TypeVar("TSession", bound=Session | AsyncSession)


def session_stub(session_cls: type[TSession]) -> Any:
    session = _make_generic_stub(session_cls)
    session.is_dirty.returns(False)
    return session


SpySession: Any = session_stub(Session)
SpyAsyncSession: Any = session_stub(AsyncSession)
