from __future__ import annotations

from abc import abstractmethod
from functools import wraps
import typing
from typing import Any, Callable, Generic, TypeVar

from aod._internal.application.cache import AsyncCache, Cache
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler import (
    AsyncCommandPort,
    AsyncQueryPort,
    CommandPort,
    QueryPort,
)
from aod._internal.core.async_utils import should_await
from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.infrastructure_exception import AbstractSessionTypeError
from aod._internal.infrastructure.session import AsyncSession, Session

TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)

_CACHE_WRAPPED_KEY = "__aod_cache_wrapped__"


def _raise_if_abstract_session(owner: str, field_name: str, tp: object) -> None:
    if tp is Session or tp is AsyncSession:
        raise AbstractSessionTypeError(owner, field_name, tp)


class BaseHandler(BaseBehaviour):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            return
        for field_name, tp in hints.items():
            _raise_if_abstract_session(cls.__name__, field_name, tp)

    def _get_sessions(self) -> list[Session | AsyncSession]:
        sessions: list[Session | AsyncSession] = []
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, (Session, AsyncSession)):
                sessions.append(value)
        return sessions

    def _get_caches(self) -> list[Cache | AsyncCache]:
        return []


class AsyncBaseHandler(BaseHandler):
    pass


class CommandHandler(BaseHandler, CommandPort, Generic[TCommand]):
    _caches: list[Cache | AsyncCache] = PrivateField(default_factory=list)

    @abstractmethod
    def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]

    def add_cache(self, cache: Cache | AsyncCache) -> None:
        self._caches.append(cache)

    def _get_caches(self) -> list[Cache | AsyncCache]:
        return list(self._caches)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_handle = cls.__dict__.get("handle")
        if (
            original_handle is not None
            and not getattr(original_handle, _CACHE_WRAPPED_KEY, False)
            and not getattr(original_handle, "__isabstractmethod__", False)
        ):
            wrapped = cls._wrap_command_handle(original_handle)
            setattr(cls, "handle", wrapped)
            setattr(wrapped, _CACHE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @staticmethod
    def _wrap_command_handle(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: Any, command: object) -> object:
            result = fn(self, command)
            for cache in self._caches:
                key = cache.get_invalidate_key(command)
                if key is not None:
                    cache.delete_promise(key)
            return result

        return wrapper


class QueryHandler(BaseHandler, QueryPort, Generic[TQuery]):
    _cache: Cache | AsyncCache | None = PrivateField(default=None)

    @abstractmethod
    def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]

    def add_cache(self, cache: Cache | AsyncCache) -> None:
        if self._cache is not None:
            raise ValueError(
                f"QueryHandler {type(self).__name__} already has a cache. "
                "A QueryHandler can only have one cache."
            )
        self._cache = cache

    def _get_caches(self) -> list[Cache | AsyncCache]:
        if self._cache is not None:
            return [self._cache]
        return []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_handle = cls.__dict__.get("handle")
        if (
            original_handle is not None
            and not getattr(original_handle, _CACHE_WRAPPED_KEY, False)
            and not getattr(original_handle, "__isabstractmethod__", False)
        ):
            wrapped = cls._wrap_query_handle(original_handle)
            setattr(cls, "handle", wrapped)
            setattr(wrapped, _CACHE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @staticmethod
    def _wrap_query_handle(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: Any, query: object) -> object:
            cache = self._cache
            cache_key = None
            if cache is not None:
                cache_key = cache.get_cache_key(query)
                result = cache.get(cache_key)
                if result is not None:
                    return result
            result = fn(self, query)
            if cache is not None and cache_key is not None:
                cache.set_promise(cache_key, result)
            return result

        return wrapper


class AsyncQueryHandler(AsyncBaseHandler, AsyncQueryPort, Generic[TQuery]):
    _cache: Cache | AsyncCache | None = PrivateField(default=None)

    @abstractmethod
    async def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]

    def add_cache(self, cache: Cache | AsyncCache) -> None:
        if self._cache is not None:
            raise ValueError(
                f"AsyncQueryHandler {type(self).__name__} already has a cache. "
                "A QueryHandler can only have one cache."
            )
        self._cache = cache

    def _get_caches(self) -> list[Cache | AsyncCache]:
        if self._cache is not None:
            return [self._cache]
        return []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_handle = cls.__dict__.get("handle")
        if (
            original_handle is not None
            and not getattr(original_handle, _CACHE_WRAPPED_KEY, False)
            and not getattr(original_handle, "__isabstractmethod__", False)
        ):
            wrapped = cls._wrap_async_query_handle(original_handle)
            setattr(cls, "handle", wrapped)
            setattr(wrapped, _CACHE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @staticmethod
    def _wrap_async_query_handle(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(self: Any, query: object) -> object:
            cache = self._cache
            cache_key = None
            if cache is not None:
                cache_key = cache.get_cache_key(query)
                result = await should_await(cache.get(cache_key))
                if result is not None:
                    return result
            result = await should_await(fn(self, query))
            if cache is not None and cache_key is not None:
                cache.set_promise(cache_key, result)
            return result

        return wrapper


class AsyncCommandHandler(AsyncBaseHandler, AsyncCommandPort, Generic[TCommand]):
    _caches: list[Cache | AsyncCache] = PrivateField(default_factory=list)

    @abstractmethod
    async def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]

    def add_cache(self, cache: Cache | AsyncCache) -> None:
        self._caches.append(cache)

    def _get_caches(self) -> list[Cache | AsyncCache]:
        return list(self._caches)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_handle = cls.__dict__.get("handle")
        if (
            original_handle is not None
            and not getattr(original_handle, _CACHE_WRAPPED_KEY, False)
            and not getattr(original_handle, "__isabstractmethod__", False)
        ):
            wrapped = cls._wrap_async_command_handle(original_handle)
            setattr(cls, "handle", wrapped)
            setattr(wrapped, _CACHE_WRAPPED_KEY, True)
        super().__init_subclass__(**kwargs)

    @staticmethod
    def _wrap_async_command_handle(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(self: Any, command: object) -> object:
            result = await fn(self, command)
            for cache in self._caches:
                key = cache.get_invalidate_key(command)
                if key is not None:
                    cache.delete_promise(key)
            return result

        return wrapper
