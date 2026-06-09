from aod._internal.core.base_behaviour import BaseBehaviour
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import PrivateField


class Service(BaseBehaviour):
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)