from __future__ import annotations

from functools import wraps
from types import UnionType
from typing import Any, Generic, TypeVar, get_args, get_origin

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.infrastructure_exception import HandlerResultTypeError
from aod._internal.core.type_handlers.generic_utils import get_last_generic_arg

T = TypeVar("T")


class BaseHandler(BaseSealed, Generic[T]):
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls._wrap_handle()

    @staticmethod
    def _make_checkable(tp: type) -> type:
        origin = get_origin(tp)
        if origin is not None and origin is not UnionType:
            return origin
        return tp

    @classmethod
    def _resolve_expected_result_type(cls) -> type:
        for orig_base in getattr(cls, "__orig_bases__", ()):
            origin = get_origin(orig_base)
            if origin is not None and issubclass(origin, BaseHandler):
                args = get_args(orig_base)
                if args and not isinstance(args[0], TypeVar):
                    result = get_last_generic_arg(args[0])
                    if result is not None:
                        return result
        return object

    @classmethod
    def _wrap_handle(cls) -> None:
        handle = cls.__dict__.get("handle")
        if handle is None or getattr(handle, "__isabstractmethod__", False):
            return
        expected = cls._resolve_expected_result_type()
        if expected is object:
            return
        checkable = cls._make_checkable(expected)

        @wraps(handle)
        def checked_handle(self: Any, *args: Any, **kwargs: Any) -> object:
            result = handle(self, *args, **kwargs)
            if not isinstance(result, checkable):
                raise HandlerResultTypeError(
                    type(self).__name__, type(result).__name__, str(expected)
                )
            return result

        cls.handle = checked_handle


class AsyncBaseHandler(BaseHandler, Generic[T]):
    @classmethod
    def _wrap_handle(cls) -> None:
        handle = cls.__dict__.get("handle")
        if handle is None or getattr(handle, "__isabstractmethod__", False):
            return
        expected = cls._resolve_expected_result_type()
        if expected is object:
            return
        checkable = cls._make_checkable(expected)

        @wraps(handle)
        async def checked_handle(self: Any, *args: Any, **kwargs: Any) -> object:
            result = await handle(self, *args, **kwargs)
            if not isinstance(result, checkable):
                raise HandlerResultTypeError(
                    type(self).__name__, type(result).__name__, str(expected)
                )
            return result

        cls.handle = checked_handle
