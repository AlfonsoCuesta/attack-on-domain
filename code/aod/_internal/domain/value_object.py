from __future__ import annotations

from aod._internal.core.base_sealed import BaseSealed
from aod._internal.core.event_emitter import EventEmitter
from aod._internal.core.fields.fields import PrivateField
from aod._internal.core.reconstructable import ReconstructMixin


class ValueObject(ReconstructMixin, BaseSealed):
    """Domain Value Object base (immutable) with domain events."""

    _event_emitter: EventEmitter = PrivateField(default_factory=EventEmitter)
