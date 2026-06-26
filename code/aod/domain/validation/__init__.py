from aod._internal.core.base_guarded import inherit_context as _inherit_context
from aod._internal.core.base_validator import make_base_model
from aod._internal.core.invariances import (
    AfterValidator,
    BeforeValidator,
    field_invariance,
    invariance,
)

# @mutable is the preferred public name; inherit_context kept for compatibility
inherit_context = _inherit_context
mutable = _inherit_context

__all__ = [
    "AfterValidator",
    "BeforeValidator",
    "field_invariance",
    "invariance",
    "inherit_context",
    "mutable",
    "make_base_model",
]
