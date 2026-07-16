from __future__ import annotations

from typing import Any, cast, get_args, get_origin, get_type_hints

from aod._internal.application.cache import Cache
from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.core.base_operation import BaseOperation
from aod._internal.core.infrastructure_exception import (
    DuplicateHandlerError,
    HandlerModelError,
    HandlerNotFoundError,
)
from aod._internal.infrastructure.container.session_manager import SessionManager
from aod._internal.infrastructure.container.types import (
    _ASYNC_HANDLERS,
    _SYNC_HANDLERS,
    AnyHandler,
    _is_session_annotation,
)
from aod._internal.infrastructure.handlers.handlers import AsyncBaseHandler


class HandlerManager:
    def __init__(
        self,
        handlers: list[AnyHandler] | None = None,
        session_manager: SessionManager | None = None,
        *,
        caches: list[Cache] | None = None,
    ) -> None:
        self._handlers: list[AnyHandler] = handlers if handlers is not None else []
        self._session_manager = session_manager
        self._caches: list[Cache] = caches if caches is not None else []
        self._validate_no_duplicates()

    @staticmethod
    def contract_from_handler(h_cls: AnyHandler) -> type[Command] | type[Query]:
        hints = get_type_hints(h_cls.handle)
        for param_type in hints.values():
            if isinstance(param_type, type) and issubclass(param_type, (Command, Query)):
                return param_type
        raise HandlerModelError(h_cls, "handle")

    def _validate_no_duplicates(self) -> None:
        seen: set[type[Command] | type[Query]] = set()
        for h_cls in self._handlers:
            contract = self.contract_from_handler(h_cls)
            if contract in seen:
                raise DuplicateHandlerError(contract.__name__)
            seen.add(contract)

    def find_handler(self, contract: type[Command] | type[Query]) -> AnyHandler:
        for h_cls in self._handlers:
            if self.contract_from_handler(h_cls) is contract:
                return h_cls
        raise HandlerNotFoundError("handler", contract.__name__)

    def _apply_caches(self, handler: _SYNC_HANDLERS | _ASYNC_HANDLERS) -> None:
        if not self._caches:
            return
        contract = self.contract_from_handler(type(handler))
        is_query = isinstance(contract, type) and issubclass(contract, Query)
        is_command = isinstance(contract, type) and issubclass(contract, Command)
        for cache in self._caches:
            if not isinstance(cache, Cache):
                continue
            if not cache.keys:
                continue
            for key_obj in cache.keys:
                if is_query and key_obj.get_query_type() is contract:
                    handler.add_cache(cache)
                    break
                if is_command and contract in key_obj.get_command_types():
                    handler.add_cache(cache)
                    break

    def get_handler(
        self, contract: type[Command] | type[Query]
    ) -> _ASYNC_HANDLERS | _SYNC_HANDLERS:
        handler = self.find_handler(contract)
        cls_hints = get_type_hints(handler)
        kwargs: dict[str, Any] = {}
        if self._session_manager is not None:
            for field_name, tp in cls_hints.items():
                if _is_session_annotation(tp):
                    kwargs[field_name] = self._session_manager.get_session(tp)

        instance = self._instantiate_handler(handler, kwargs)
        self._apply_caches(instance)
        return instance

    def _instantiate_handler(
        self,
        handler: type[_ASYNC_HANDLERS | _SYNC_HANDLERS],
        kwargs: dict[str, Any],
    ) -> _ASYNC_HANDLERS | _SYNC_HANDLERS:
        if issubclass(handler, AsyncBaseHandler):
            return cast(_ASYNC_HANDLERS, handler(**kwargs))
        return cast(_SYNC_HANDLERS, handler(**kwargs))

    def inject_handlers(self, operation_cls: type[BaseOperation], kwargs: dict[str, Any]) -> None:
        for field_name, field_info in operation_cls.__model_fields__.items():
            if field_name in kwargs:
                continue
            field_type = field_info.annotation
            origin = get_origin(field_type)
            if (
                origin is None
                or not isinstance(origin, type)
                or not issubclass(origin, HandlerProtocol)
            ):
                continue
            args = get_args(field_type)
            contract = args[0]
            if isinstance(contract, type) and issubclass(contract, (Command, Query)):
                kwargs[field_name] = self.get_handler(contract)
