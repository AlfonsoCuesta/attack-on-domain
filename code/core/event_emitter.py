from typing import List, Protocol, runtime_checkable


class Event:
    pass


@runtime_checkable
class EventEmitter(Protocol):
    def _emit(self, event: Event) -> None:
        pass

    def _clear_events(self) -> None:
        pass

    def poll_events(self) -> List[Event]:
        pass
