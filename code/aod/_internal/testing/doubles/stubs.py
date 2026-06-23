from __future__ import annotations

import inspect
from inspect import iscoroutinefunction
from typing import Any, Callable, TypeVar, cast

from aod._internal.application.port import Port

T = TypeVar("T")
TPort = TypeVar("TPort", bound=Port)


class Params:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._args = args
        self._kwargs = kwargs

    def args(self) -> tuple[Any, ...]:
        return self._args

    def kwargs(self) -> dict[str, Any]:
        return self._kwargs


class MethodStub:
    def __init__(self, original: Callable[..., Any] | None = None) -> None:
        self._original = original
        self._returns: list[Any] = []
        self._calls: list[Params] = []
        self._always_returns: Any = None
        self._raise: Exception | None = None

    def returns(self, *values: Any) -> None:
        self._always_returns = None
        self._returns = list(values)

    def always_returns(self, value: Any) -> None:
        self._returns = []
        self._always_returns = value

    def raises(self, exc: Exception) -> None:
        self._raise = exc

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._call(*args, **kwargs)

    def _call(self, *args: Any, **kwargs: Any) -> Any:
        self._calls.append(Params(*args, **kwargs))
        if self._raise is not None:
            exc, self._raise = self._raise, None
            raise exc
        if self._original is not None:
            sig = inspect.signature(self._original)
            try:
                if hasattr(self._original, "__self__"):
                    sig.bind(*args, **kwargs)
                else:
                    sig.bind(None, *args, **kwargs)
            except TypeError:
                raise
        if self._returns:
            return self._returns.pop(0)
        return self._always_returns

    @property
    def calls(self) -> list[Params]:
        return list(self._calls)

    @property
    def called(self) -> bool:
        return len(self._calls) > 0

    @property
    def call_count(self) -> int:
        return len(self._calls)


class AsyncMethodStub(MethodStub):
    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._call(*args, **kwargs)


def port_stub(port_cls: type[TPort]) -> Any:
    return _make_generic_stub(port_cls)


def _make_callable_stub(func: Callable[..., Any]) -> Any:
    return (
        AsyncMethodStub(original=func) if iscoroutinefunction(func) else MethodStub(original=func)
    )


def _make_generic_stub(cls: type[T]) -> Any:
    stubs: dict[str, Any] = {}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        attr = getattr(cls, name, None)
        if callable(attr):
            stubs[name] = _make_callable_stub(attr)

    stub_cls = type(f"Stub{cls.__name__}", (cls,), stubs)

    for name, stub in stubs.items():
        if getattr(stub_cls, name) is not stub:
            setattr(stub_cls, name, stub)

    return cast(type[T], stub_cls)
