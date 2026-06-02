from __future__ import annotations

from typing import Any, Self

from .base_validator import _use_raw_model


class ReconstructMixin:
    @classmethod
    def reconstruct(cls, **kwargs: Any) -> Self:
        token = _use_raw_model.set(True)
        try:
            return cls(**kwargs)
        finally:
            _use_raw_model.reset(token)
