from abc import abstractmethod
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Callable, Generic, TypeVar

from aod._internal.application.cache.cache_manager import get_cache_context
from aod._internal.application.contracts import Command, PolicyContract, Query
from aod._internal.application.port import Port
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases

TResult = TypeVar("TResult")
TEntity = TypeVar("TEntity")
TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)
TPolicyContract = TypeVar("TPolicyContract", bound=PolicyContract)

_CACHE_WRAPPED_KEY = "__aod_handler_cache_wrapped__"


class HandlerProtocol(Port):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "handle") or not callable(cls.handle):
            return
        _wrap_handler_validation(cls)
        base_names = {base.__name__ for base in cls.__mro__}
        is_command = bool(base_names & {"CommandPort", "AsyncCommandPort"})
        is_query = bool(base_names & {"QueryPort", "AsyncQueryPort"})
        if (
            (is_command or is_query)
            and not getattr(cls.handle, "__isabstractmethod__", False)
            and not getattr(cls.handle, _CACHE_WRAPPED_KEY, False)
        ):
            _wrap_handler_cache(cls)


def _wrap_handler_validation(cls: type) -> None:
    original_handle = getattr(cls, "handle")
    expected_type = _extract_expected_type(cls)
    if expected_type is None or isinstance(expected_type, TypeVar):
        return
    if iscoroutinefunction(original_handle):
        validate_handle = _make_async_validate_handle(original_handle, expected_type)
    else:
        validate_handle = _make_validate_handle(original_handle, expected_type)
    setattr(cls, "handle", validate_handle)


def _make_validate_handle(original_handle: Callable, expected_type: type) -> Callable:
    @wraps(original_handle)
    def validate_handle(self: Any, contract: Any, **kwargs: Any) -> Any:
        begin_sessions = getattr(self, "_begin_sessions", None)
        if callable(begin_sessions):
            begin_sessions()
        if not isinstance(contract, expected_type):
            raise TypeError(f"Expected {expected_type.__name__}, got {type(contract).__name__}")
        return original_handle(self, contract, **kwargs)

    return validate_handle


def _make_async_validate_handle(original_handle: Callable, expected_type: type) -> Callable:
    @wraps(original_handle)
    async def validate_handle(self: Any, contract: Any, **kwargs: Any) -> Any:
        begin_sessions = getattr(self, "_begin_sessions_async", None)
        if callable(begin_sessions):
            await begin_sessions()
        if not isinstance(contract, expected_type):
            raise TypeError(f"Expected {expected_type.__name__}, got {type(contract).__name__}")
        return await original_handle(self, contract, **kwargs)

    return validate_handle


def _wrap_handler_cache(cls: type) -> None:
    original_handle = getattr(cls, "handle")
    is_query = QueryPort in cls.__mro__ or AsyncQueryPort in cls.__mro__
    if iscoroutinefunction(original_handle):
        cache_handle = _make_async_cache_handle(original_handle, is_query)
    else:
        cache_handle = _make_cache_handle(original_handle, is_query)
    setattr(cache_handle, _CACHE_WRAPPED_KEY, True)
    setattr(cls, "handle", cache_handle)


def _make_cache_handle(original_handle: Callable, is_query: bool) -> Callable:
    @wraps(original_handle)
    def cache_handle(self: Any, contract: Any, **kwargs: Any) -> Any:
        ctx = get_cache_context()
        if is_query:
            cached = ctx.get(contract)
            if cached is not None:
                return cached
        result = original_handle(self, contract, **kwargs)
        if is_query:
            if result is not None:
                ctx.set(contract, result)
        else:
            ctx.delete(contract)
        return result

    return cache_handle


def _make_async_cache_handle(original_handle: Callable, is_query: bool) -> Callable:
    @wraps(original_handle)
    async def cache_handle(self: Any, contract: Any, **kwargs: Any) -> Any:
        ctx = get_cache_context()
        if is_query:
            cached = await ctx.get_async(contract)
            if cached is not None:
                return cached
        result = await original_handle(self, contract, **kwargs)
        if is_query:
            if result is not None:
                await ctx.set_async(contract, result)
        else:
            ctx.delete(contract)
        return result

    return cache_handle


def _extract_expected_type(cls: type) -> type | None:
    for base in getattr(cls, "__orig_bases__", ()):
        origin = getattr(base, "__origin__", None)
        if origin is None:
            continue
        if isinstance(origin, type) and issubclass(origin, HandlerProtocol):
            return get_generic_arg_from_orig_bases(cls, origin)
    return None


class CommandPort(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class QueryPort(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: Query[TEntity, TResult]) -> TResult: ...


class AsyncCommandPort(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class AsyncQueryPort(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: Query[TEntity, TResult]) -> TResult: ...


class PolicyPort(HandlerProtocol, Generic[TPolicyContract]):
    @abstractmethod
    def handle(self, contract: TPolicyContract) -> None: ...


class AsyncPolicyPort(HandlerProtocol, Generic[TPolicyContract]):
    @abstractmethod
    async def handle(self, contract: TPolicyContract) -> None: ...
