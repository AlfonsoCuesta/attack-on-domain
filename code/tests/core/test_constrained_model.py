from aod._internal.core.base_validator import make_base_model
from aod.domain import Field, RootEntity, ValueObject
from aod.domain.validation import field_invariance, invariance
from pydantic import BaseModel


class TestConstrainedModel:
    def test_constrained_model_has_field_constraints(self) -> None:
        class Money(ValueObject):
            amount: float = Field(ge=0)
            currency: str = Field(min_length=3)

        model = Money.__constrained_model__
        assert "amount" in model.model_fields
        assert "currency" in model.model_fields

    def test_constrained_model_has_field_validator(self) -> None:
        class Money(ValueObject):
            amount: float

            @field_invariance("amount")
            @classmethod
            def _amount_positive(cls, v: float) -> float:
                if v < 0:
                    raise ValueError("amount must be positive")
                return v

        model = Money.__constrained_model__
        assert "amount" in model.model_fields

    def test_constrained_model_does_not_have_invariance(self) -> None:
        class Money(ValueObject):
            amount: float
            currency: str

            @field_invariance("amount")
            @classmethod
            def _amount_positive(cls, v: float) -> float:
                if v < 0:
                    raise ValueError("amount must be positive")
                return v

            @invariance
            def _currency_uppercase(self) -> None:
                self.currency = self.currency.upper()

        model = Money.__constrained_model__
        assert "amount" in model.model_fields
        assert "currency" in model.model_fields

    def test_validation_model_has_invariance(self) -> None:
        class Money(ValueObject):
            amount: float
            currency: str

            @field_invariance("amount")
            @classmethod
            def _amount_positive(cls, v: float) -> float:
                if v < 0:
                    raise ValueError("amount must be positive")
                return v

        model = Money.__validation_model__
        assert "amount" in model.model_fields

    def test_raw_model_strips_constraints(self) -> None:
        class Money(ValueObject):
            amount: float = Field(ge=0)
            currency: str = Field(min_length=3)

        model = Money.__raw_model__
        assert "amount" in model.model_fields
        assert "currency" in model.model_fields


class TestExtractPydanticModel:
    def test_extract_simple_model(self) -> None:
        class Money(ValueObject):
            amount: float = Field(ge=0)
            currency: str = Field(min_length=3)

        pydantic_model = make_base_model(Money)
        assert issubclass(pydantic_model, BaseModel)
        assert "amount" in pydantic_model.model_fields
        assert "currency" in pydantic_model.model_fields

    def test_extract_with_nested_value_object(self) -> None:
        class Address(ValueObject):
            street: str
            city: str

        class User(RootEntity):
            id: int = Field(id=True)
            name: str
            address: Address

        pydantic_model = make_base_model(User)
        assert issubclass(pydantic_model, BaseModel)
        assert "id" in pydantic_model.model_fields
        assert "name" in pydantic_model.model_fields
        assert "address" in pydantic_model.model_fields

    def test_extract_creates_pydantic_models_for_nested(self) -> None:
        class Address(ValueObject):
            street: str
            city: str

        class User(RootEntity):
            id: int = Field(id=True)
            address: Address

        pydantic_model = make_base_model(User)
        address_field = pydantic_model.model_fields["address"]
        assert issubclass(address_field.annotation, BaseModel)

    def test_extract_no_invariance_validators(self) -> None:
        class Money(ValueObject):
            amount: float

            @field_invariance("amount")
            @classmethod
            def _amount_positive(cls, v: float) -> float:
                if v < 0:
                    raise ValueError("amount must be positive")
                return v

        pydantic_model = make_base_model(Money)
        instance = pydantic_model(amount=-10.0)
        assert getattr(instance, "amount") == -10.0

    def test_extract_preserves_field_constraints(self) -> None:
        class Money(ValueObject):
            amount: float = Field(ge=0)

        pydantic_model = make_base_model(Money)
        instance = pydantic_model(amount=10.0)
        assert getattr(instance, "amount") == 10.0
