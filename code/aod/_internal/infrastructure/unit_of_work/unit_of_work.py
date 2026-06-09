from __future__ import annotations

from aod._internal.application.port import Port
from aod._internal.core.async_utils import should_await
from aod._internal.core.fields.fields import Field
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.session import AsyncSession, Session


class UnitOfWork(Port):
    sessions: set[Session] = Field(default_factory=set)

    def commit(self) -> None:
        token = _CommitContext.set(True)
        try:
            for s in self.sessions:
                if s.is_dirty():
                    s.commit()
        finally:
            _CommitContext.reset(token)

    def rollback(self) -> None:
        for s in self.sessions:
            if s.is_dirty():
                s.rollback()

    def flush(self) -> None:
        for s in self.sessions:
            s.flush()


class AsyncUnitOfWork(Port):
    sessions: set[Session | AsyncSession] = Field(default_factory=set)

    async def commit(self) -> None:
        token = _CommitContext.set(True)
        try:
            for s in self.sessions:
                if s.is_dirty():
                    await should_await(s.commit())
        finally:
            _CommitContext.reset(token)

    async def rollback(self) -> None:
        for s in self.sessions:
            if s.is_dirty():
                await should_await(s.rollback())

    async def flush(self) -> None:
        for s in self.sessions:
            await should_await(s.flush())