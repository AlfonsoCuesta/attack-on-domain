from __future__ import annotations

from abc import abstractmethod
from functools import wraps
from typing import Any, Callable, ClassVar

from aod._internal.core.base_guarded import inherit_context
from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.event_emitter import Event, EventCollector, EventEmitter
from aod._internal.core.fields.fields import Field, PrivateField

_USE_CASE_WRAPPED_KEY = "__aod_use_case_wrapped__"


def _wrap_run_with_collector(fn: Callable[..., None]) -> Callable[..., None]:
    @wraps(fn)
    def wrapper(self: UseCase, *args: Any, **kwargs: Any) -> None:
        with EventCollector() as events:
            try:
                fn(self, *args, **kwargs)
            finally:
                self.events = list(events)

    setattr(wrapper, _USE_CASE_WRAPPED_KEY, True)
    return wrapper


class UseCase(BaseSealed):
    __skip_method_wrapping__: ClassVar[bool] = True
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
    events: list[Event] = Field(default_factory=list, init=False)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        original_run: Callable[..., None] | None = cls.__dict__.get("run")
        if original_run is not None and not getattr(original_run, _USE_CASE_WRAPPED_KEY, False):
            setattr(cls, "run", _wrap_run_with_collector(original_run))
        super().__init_subclass__(**kwargs)

    @abstractmethod
    @inherit_context
    def run(self) -> None: ...
