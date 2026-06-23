from __future__ import annotations

import inspect
from inspect import iscoroutinefunction
from typing import Any, Callable, TypeVar, cast

from aod._internal.application.port import Port

T = TypeVar("T")
TPort = TypeVar("TPort", bound=Port)


class MethodStub:
    def __init__(self, original: Callable[..., Any] | None = None) -> None:
        self._original = original
        self._returns: list[Any] = []
        self._calls: list[list[Any]] = []
        self._always_returns: Any = None

    def returns(self, *values: Any) -> None:
        self._always_returns = None
        self._returns = list(values)

    def always_returns(self, value: Any) -> None:
        self._returns = []
        self._always_returns = value

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._original is not None and kwargs:
            sig = inspect.signature(self._original)
            for key in kwargs:
                if key not in sig.parameters:
                    raise TypeError(
                        f"{self._original.__name__}() got an unexpected keyword argument '{key}'"
                    )
        self._calls.append(list(args) + list(kwargs.values()))
        if self._returns:
            return self._returns.pop(0)
        return self._always_returns

    @property
    def calls(self) -> list[list[Any]]:
        return list(self._calls)

    @property
    def called(self) -> bool:
        return len(self._calls) > 0

    @property
    def call_count(self) -> int:
        return len(self._calls)


class AsyncMethodStub:
    def __init__(self, original: Callable[..., Any] | None = None) -> None:
        self._original = original
        self._returns: list[Any] = []
        self._calls: list[list[Any]] = []
        self._always_returns: Any = None

    def returns(self, *values: Any) -> None:
        self._always_returns = None
        self._returns = list(values)

    def always_returns(self, value: Any) -> None:
        self._returns = []
        self._always_returns = value

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._original is not None and kwargs:
            sig = inspect.signature(self._original)
            for key in kwargs:
                if key not in sig.parameters:
                    raise TypeError(
                        f"{self._original.__name__}() got an unexpected keyword argument '{key}'"
                    )
        self._calls.append(list(args) + list(kwargs.values()))
        if self._returns:
            return self._returns.pop(0)
        return self._always_returns

    @property
    def calls(self) -> list[list[Any]]:
        return list(self._calls)

    @property
    def called(self) -> bool:
        return len(self._calls) > 0

    @property
    def call_count(self) -> int:
        return len(self._calls)


def port_stub(port_cls: type[TPort]) -> Any:
    return _make_generic_stub(port_cls)


def _make_callable_stub(func: Callable[..., Any]) -> Any:
    return (
        AsyncMethodStub(original=func) if iscoroutinefunction(func) else MethodStub(original=func)
    )


def _make_generic_stub(cls: type[T]) -> Any:
    methods: dict[str, Any] = {}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name, None)
        if callable(attr):
            stub = _make_callable_stub(attr)
            methods[name] = stub
    return cast(type[T], type(f"Stub{cls.__name__}", (cls,), methods))
