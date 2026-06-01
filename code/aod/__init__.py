"""
Public API for the aod library.

Supported imports: ``from aod import …`` only. The ``_internal`` package
exists for packaging layout only; it is not a semver-stable API surface.
"""

from aod._internal.core.event_emitter import Event as DomainEvent
from aod._internal.core.event_emitter import EventCollector
from aod._internal.core.fields.fields import Field, PrivateField
from aod._internal.domain.app import App
from aod._internal.domain.bounded_context import BoundedContext
from aod._internal.domain.entity import Entity, RootEntity
from aod._internal.domain.service import Service
from aod._internal.domain.value_object import ValueObject

__all__ = [
    "App",
    "BoundedContext",
    "DomainEvent",
    "EventCollector",
    "Entity",
    "RootEntity",
    "Service",
    "ValueObject",
    "Field",
    "PrivateField",
]
