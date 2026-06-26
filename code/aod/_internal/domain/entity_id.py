from __future__ import annotations

from typing import Any, Self

from aod._internal.core.base_guarded import inherit_context
from aod._internal.core.fields.fields import PrivateField
from aod._internal.domain.value_object import ValueObject


class EntityId(ValueObject):
    """Entity identity with change tracking.

    Each identity carries a ``_last_id`` reference to the previous identity,
    enabling the persistence layer to find and update the original row.
    """

    _last_id: Self | None = PrivateField(default=None)

    @inherit_context
    def evolve(self, **changes: Any) -> Self:
        """Create a new identity with ``changes`` applied, linking to the previous one.

        Fields not present in ``changes`` keep their current values.
        If this identity already has a ``_last_id``, the new identity inherits
        the *original* (oldest) link, so the chain always points to the first
        identity in the sequence.
        """
        fields = {k: getattr(self, k) for k in type(self).__model_fields__}
        fields.update(changes)
        old_last = self._last_id or self
        new = self.__class__(**fields)
        object.__setattr__(new, "_last_id", old_last)
        return new
