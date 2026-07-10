from __future__ import annotations

from typing import Any

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.unit_of_work.unit_of_work import (
    AsyncUnitOfWork as AppAsyncUnitOfWork,
)
from aod._internal.application.unit_of_work.unit_of_work import UnitOfWork as AppUnitOfWork
from aod._internal.core.async_utils import should_await
from aod._internal.core.fields.fields import Field
from aod._internal.infrastructure.commit_context import _CommitContext
from aod._internal.infrastructure.session import AsyncSession, Session


class UnitOfWork(AppUnitOfWork):
    sessions: set[Session] = Field(default_factory=set)
    caches: set[Cache | AsyncCache] = Field(default_factory=set)

    def add_handler(self, handler: Any) -> None:
        for session in handler._get_sessions():
            self.sessions.add(session)
        for cache in handler._get_caches():
            self.caches.add(cache)

    def commit(self) -> None:
        token = _CommitContext.set(True)
        try:
            for s in self.sessions:
                if s.is_dirty():
                    s.commit()
            for cache in self.caches:
                cache._flush()
        finally:
            _CommitContext.reset(token)

    def rollback(self) -> None:
        for s in self.sessions:
            if s.is_dirty():
                s.rollback()

    def begin(self) -> None:
        for s in self.sessions:
            s.begin()


class AsyncUnitOfWork(AppAsyncUnitOfWork):
    sessions: set[Session | AsyncSession] = Field(default_factory=set)
    caches: set[Cache | AsyncCache] = Field(default_factory=set)

    def add_handler(self, handler: Any) -> None:
        for session in handler._get_sessions():
            self.sessions.add(session)
        for cache in handler._get_caches():
            self.caches.add(cache)

    async def commit(self) -> None:
        token = _CommitContext.set(True)
        try:
            for s in self.sessions:
                if s.is_dirty():
                    await should_await(s.commit())
            for cache in self.caches:
                await should_await(cache._flush())
        finally:
            _CommitContext.reset(token)

    async def rollback(self) -> None:
        for s in self.sessions:
            if s.is_dirty():
                await should_await(s.rollback())

    async def begin(self) -> None:
        for s in self.sessions:
            await should_await(s.begin())
