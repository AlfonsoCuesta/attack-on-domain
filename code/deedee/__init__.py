"""
Public API for the deedee library.

Supported imports: ``from deedee import …`` only. The ``_internal`` package
exists for packaging layout only; it is not a semver-stable API surface.
"""

from deedee._internal.core.domain_exception import DomainException
from deedee._internal.core.event_emitter import Event as DomainEvent
from deedee._internal.domain.bounded_context import BoundedContext
from deedee._internal.domain.entity import Entity, RootEntity
from deedee._internal.domain.value_object import ValueObject

__all__ = [
    "BoundedContext",
    "DomainEvent",
    "DomainException",
    "Entity",
    "RootEntity",
    "ValueObject",
]
