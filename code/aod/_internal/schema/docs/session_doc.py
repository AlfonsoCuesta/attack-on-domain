from __future__ import annotations

import inspect
from dataclasses import dataclass

from aod._internal.infrastructure.session import AsyncSession, Session


@dataclass
class SessionDoc:
    name: str
    description: str = ""
    is_async: bool = False

    @classmethod
    def from_session(cls, session_cls: type[Session] | type[AsyncSession]) -> SessionDoc:
        return cls(
            name=session_cls.__name__,
            description=inspect.getdoc(session_cls) or "",
            is_async=issubclass(session_cls, AsyncSession),
        )
