from __future__ import annotations

from inspect import iscoroutinefunction
from typing import Any, Callable, TypeVar, cast
from unittest.mock import AsyncMock, MagicMock, Mock

from aod._internal.application.port import Port

T = TypeVar("T")
TPort = TypeVar("TPort", bound=Port)


def port_stub(port_cls: type[TPort]) -> Any:
    return _make_generic_stub(port_cls)


def _make_callable_stub(func: Callable[..., Any]) -> Any:
    mock_cls = AsyncMock if iscoroutinefunction(func) else MagicMock
    mock = mock_cls(spec=func)
    name = getattr(func, "__name__", "")
    mock.__name__ = name
    mock.__qualname__ = getattr(func, "__qualname__", name)
    mock.__type_params__ = getattr(func, "__type_params__", ())
    mock.return_value = None
    if getattr(mock, "__isabstractmethod__", False):
        mock.__isabstractmethod__ = False
    return mock


def _make_generic_stub(cls: type[T]) -> Any:
    stubs: dict[str, Any] = {
        "__skip_method_wrapping__": True,
    }
    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name, None)
        if isinstance(attr, Mock):
            stubs[name] = attr
        elif callable(attr):
            stubs[name] = _make_callable_stub(attr)

    stub_cls = type(f"Stub{cls.__name__}", (cls,), stubs)

    for name, stub in stubs.items():
        if name.startswith("_"):
            continue
        if getattr(stub_cls, name) is not stub:
            setattr(stub_cls, name, stub)

    return cast(type[T], stub_cls)
