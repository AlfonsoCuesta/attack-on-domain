from abc import abstractmethod
from functools import wraps
from typing import Any, Generic, TypeVar

from aod._internal.application.contracts import Command, Query
from aod._internal.application.port import Port
from aod._internal.core.type_handlers.generic_utils import get_generic_arg_from_orig_bases

TResult = TypeVar("TResult")
TEntity = TypeVar("TEntity")
TCommand = TypeVar("TCommand", bound=Command)
TQuery = TypeVar("TQuery", bound=Query)

_HANDLER_ORIGINS: dict[str, type] = {}


class HandlerProtocol(Port):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "handle") or not callable(cls.handle):
            return
        original_handle = cls.handle
        expected_type = _extract_expected_type(cls)
        if expected_type is not None and not isinstance(expected_type, TypeVar):

            @wraps(original_handle)
            def validate_handle(self: Any, contract: Any, **kwargs: Any) -> Any:
                if not isinstance(contract, expected_type):
                    raise TypeError(
                        f"Expected {expected_type.__name__}, got {type(contract).__name__}"
                    )
                return original_handle(self, contract, **kwargs)

            cls.handle = validate_handle


def _extract_expected_type(cls: type) -> type | None:
    for base in getattr(cls, "__orig_bases__", ()):
        origin = getattr(base, "__origin__", None)
        if origin is None:
            continue
        origin_name = getattr(origin, "__name__", "")
        if origin_name in (
            "CommandHandler",
            "QueryHandler",
            "AsyncCommandHandler",
            "AsyncQueryHandler",
        ):
            return get_generic_arg_from_orig_bases(cls, origin)
    return None


class CommandHandler(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class QueryHandler(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    def handle(self, query: Query[TEntity, TResult]) -> TResult: ...


class AsyncCommandHandler(HandlerProtocol, Generic[TCommand]):
    @abstractmethod
    async def handle(self, command: Command[TEntity, TResult]) -> TResult: ...


class AsyncQueryHandler(HandlerProtocol, Generic[TQuery]):
    @abstractmethod
    async def handle(self, query: Query[TEntity, TResult]) -> TResult: ...
