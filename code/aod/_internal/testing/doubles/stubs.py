from __future__ import annotations

from inspect import iscoroutinefunction
from typing import Any, TypeVar, cast

from aod._internal.application.port import Port

T = TypeVar("T")
TPort = TypeVar("TPort", bound=Port)


class MethodStub:
    def __init__(self) -> None:
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
    def __init__(self) -> None:
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


def _make_generic_stub(cls: type[T]) -> Any:
    methods: dict[str, Any] = {}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name, None)
        if callable(attr):
            stub = AsyncMethodStub() if iscoroutinefunction(attr) else MethodStub()
            methods[name] = stub
    return cast(type[T], type(f"Stub{cls.__name__}", (cls,), methods))
