from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import PrivateField


class Service(BaseSealed):
    """Domain service base class (stateless, no mutation)."""

    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
