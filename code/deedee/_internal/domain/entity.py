from __future__ import annotations

from typing import ClassVar, Generator, List

from deedee._internal.core.base_mutable import BaseMutable, MutableBaseMeta
from deedee._internal.core.event_emitter import Event, EventEmitter
from deedee._internal.core.fields import PrivateField


class EntityMeta(MutableBaseMeta):
    def __new__(mcls, name, bases, namespace, root=None):
        cls = super().__new__(mcls, name, bases, namespace)
        if root is not None:
            cls.__aggregate_root__ = bool(root)
        return cls


class Entity(BaseMutable, metaclass=EntityMeta):
    __aggregate_root__: ClassVar[bool] = False
    _events: List[Event] = PrivateField(default_factory=list)

    @classmethod
    def is_root(cls) -> bool:
        return cls.__aggregate_root__

    def _emit(self, event: Event) -> None:
        self._events.append(event)

    def poll_events(self) -> List[Event]:
        events: list[Event] = list(self._events)

        for emitter in self._self_emitters():
            events.extend(emitter.poll_events())

        events.sort(key=lambda e: e.emmited_at)
        return events

    def _clear_events(self) -> None:
        self._events.clear()

        for emitter in self._self_emitters():
            emitter._clear_events()

    def _self_emitters(self) -> Generator[EventEmitter, None, None]:
        for emitter in vars(self).values():
            if isinstance(emitter, EventEmitter):
                yield emitter


class RootEntity(Entity, root=True):
    pass
