from __future__ import annotations

from typing import Any, cast, get_args, get_origin, get_type_hints

from aod._internal.application.contracts import Command, Query
from aod._internal.application.handler.handler import HandlerProtocol
from aod._internal.core.application_exception import InvalidHandlerPortFieldError
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
)
from aod._internal.infrastructure.handlers.handlers import AsyncBaseHandler
from aod._internal.infrastructure.session import AsyncSession, Session


class HandlerManager:
    def __init__(
        self,
        handlers: list[AnyHandler] | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        self._handlers: list[AnyHandler] = handlers if handlers is not None else []
        self._session_manager = session_manager
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

    def get_handler(
        self, contract: type[Command] | type[Query]
    ) -> _ASYNC_HANDLERS | _SYNC_HANDLERS:
        handler = self.find_handler(contract)
        cls_hints = get_type_hints(handler)
        try:
            session_type = cls_hints["session"]
        except KeyError:
            raise HandlerModelError(handler, "session")
        session: Session | AsyncSession | None = None
        if session_type is not type(None) and self._session_manager is not None:
            session = self._session_manager.get_session(session_type)

        return self._instantiate_handler(handler, session)

    def _instantiate_handler(
        self,
        handler: type[_ASYNC_HANDLERS | _SYNC_HANDLERS],
        session: Session | AsyncSession | None,
    ) -> _ASYNC_HANDLERS | _SYNC_HANDLERS:
        if issubclass(handler, AsyncBaseHandler):
            return cast(_ASYNC_HANDLERS, handler(session=cast(AsyncSession | None, session)))
        return cast(_SYNC_HANDLERS, handler(session=cast(Session | None, session)))

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
            if not args:
                raise InvalidHandlerPortFieldError(field_name, operation_cls.__name__)
            contract = args[0]
            if isinstance(contract, type) and issubclass(contract, (Command, Query)):
                kwargs[field_name] = self.get_handler(contract)
