from aod._internal.core.event_emitter import EventEmitter


class Service:
    """Domain service base class (stateless operations / coordination)."""

    def __init__(self) -> None:
        object.__setattr__(self, "_event_emitter", EventEmitter())
