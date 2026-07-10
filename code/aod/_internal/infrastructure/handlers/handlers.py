from __future__ import annotations

import typing
from abc import abstractmethod
from functools import wraps
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


def _ensure_handle_wrapped(
    cls: type, wrapper_fn: Callable[[Any], Any], cache_wrapped_key: str
) -> None:
    original_handle = cls.__dict__.get("handle")
    if (
        original_handle is None
        or getattr(original_handle, cache_wrapped_key, False)
        or getattr(original_handle, "__isabstractmethod__", False)
    ):
        return
    wrapped = wrapper_fn(original_handle)
    setattr(cls, "handle", wrapped)
    setattr(wrapped, cache_wrapped_key, True)


class BaseHandler(BaseBehaviour):
    _caches: list[Cache | AsyncCache] = PrivateField(default_factory=list)

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            return
        for field_name, tp in hints.items():
            _raise_if_abstract_session(cls.__name__, field_name, tp)

    def add_cache(self, cache: Cache | AsyncCache) -> None:
        self._caches.append(cache)

    def _get_sessions(self) -> list[Session | AsyncSession]:
        sessions: list[Session | AsyncSession] = []
        for field_name in self.__model_fields__:
            value = object.__getattribute__(self, field_name)
            if isinstance(value, (Session, AsyncSession)):
                sessions.append(value)
        return sessions

    def _get_caches(self) -> list[Cache | AsyncCache]:
        return list(self._caches)


class AsyncBaseHandler(BaseHandler):
    pass


class CommandHandler(BaseHandler, CommandPort, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        _ensure_handle_wrapped(cls, cls._make_cache_wrapper, _CACHE_WRAPPED_KEY)
        super().__init_subclass__(**kwargs)

    @classmethod
    def _make_cache_wrapper(cls, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: Any, command: object) -> object:
            result = fn(self, command)
            for cache in self._caches:
                cache._delete(command)
            return result

        return wrapper


class QueryHandler(BaseHandler, QueryPort, Generic[TQuery]):
    _cache: Cache | AsyncCache | None = PrivateField(default=None)

    @abstractmethod
    def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]

    def add_cache(self, cache: Cache | AsyncCache) -> None:
        if self._cache is not None:
            raise ValueError(f"{type(self).__name__} already has a cache.")
        self._cache = cache

    def _get_caches(self) -> list[Cache | AsyncCache]:
        if self._cache is not None:
            return [self._cache]
        return []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        _ensure_handle_wrapped(cls, cls._make_cache_wrapper, _CACHE_WRAPPED_KEY)
        super().__init_subclass__(**kwargs)

    @classmethod
    def _make_cache_wrapper(cls, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(self: Any, query: object) -> object:
            cache = self._cache
            if cache is not None:
                result = cache._get(query)
                if result is not None:
                    return result
            result = fn(self, query)
            if cache is not None:
                cache._set(query, result)
            return result

        return wrapper


class AsyncQueryHandler(AsyncBaseHandler, AsyncQueryPort, Generic[TQuery]):
    _cache: Cache | AsyncCache | None = PrivateField(default=None)

    @abstractmethod
    async def handle(self, query: TQuery) -> object: ...  # ty:ignore[invalid-method-override]

    def add_cache(self, cache: Cache | AsyncCache) -> None:
        if self._cache is not None:
            raise ValueError(f"{type(self).__name__} already has a cache.")
        self._cache = cache

    def _get_caches(self) -> list[Cache | AsyncCache]:
        if self._cache is not None:
            return [self._cache]
        return []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        _ensure_handle_wrapped(cls, cls._make_cache_wrapper, _CACHE_WRAPPED_KEY)
        super().__init_subclass__(**kwargs)

    @classmethod
    def _make_cache_wrapper(cls, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(self: Any, query: object) -> object:
            cache = self._cache
            if cache is not None:
                result = await should_await(cache._get(query))
                if result is not None:
                    return result
            result = await should_await(fn(self, query))
            if cache is not None:
                cache._set(query, result)
            return result

        return wrapper


class AsyncCommandHandler(AsyncBaseHandler, AsyncCommandPort, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: TCommand) -> object: ...  # ty:ignore[invalid-method-override]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        _ensure_handle_wrapped(cls, cls._make_cache_wrapper, _CACHE_WRAPPED_KEY)
        super().__init_subclass__(**kwargs)

    @classmethod
    def _make_cache_wrapper(cls, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapper(self: Any, command: object) -> object:
            result = await fn(self, command)
            for cache in self._caches:
                cache._delete(command)
            return result

        return wrapper
