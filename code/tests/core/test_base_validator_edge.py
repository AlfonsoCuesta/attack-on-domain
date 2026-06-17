from __future__ import annotations

import pytest
from aod._internal.core.base_validator import BaseValidator, make_base_model


class TestMakeBaseModel:
    def test_raises_type_error_for_non_base_validator(self) -> None:
        class _NotAValidator:
            pass

        with pytest.raises(TypeError, match="is not a BaseValidation subclass"):
            make_base_model(_NotAValidator)  # type: ignore

    def test_empty_validator_returns_constrained_model(self) -> None:
        class _EmptyValidator(BaseValidator):
            pass

        result = make_base_model(_EmptyValidator)
        assert result is _EmptyValidator.__constrained_model__
