from __future__ import annotations

from aod._internal.core.base_guarded import BaseGuarded
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.reconstructable import ReconstructMixin


class Entity(ReconstructMixin, BaseGuarded):
    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)


class RootEntity(Entity):
    pass
