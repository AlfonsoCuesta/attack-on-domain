# BaseValidator & ValidationModelMeta

## Purpose

`BaseValidator` is the foundation of the validation system. It provides a Pydantic-powered base class that auto-generates two models per class, enabling a dual-mode construction path (validated vs. raw).

## ValidationModelMeta (metaclass, única metaclass del framework)

On every class creation, the metaclass:

1. Calls `make_validation_model(cls, name, bases)` → generates a Pydantic `BaseModel` subclass with all validators, stored as `__validation_model__`
2. Calls `make_raw_model(cls, name, bases)` → generates a Pydantic `BaseModel` subclass with validators stripped, stored as `__raw_model__`
3. Sets `__model_fields__` from the validation model's `model_fields`
4. Overrides `cls.__init__.__signature__` to match the validation model's constructor signature

Acepta `**kwargs` y los pasa a `type.__new__` para no interceptar argumentos de clase como `root=True` en `Entity`.

## BaseValidator

### `__init__(**kwargs)`
Checks the `_use_raw_model` ContextVar:
- If `True` → validates using `__raw_model__` (no field validators, no `@invariance`)
- If `False` (default) → validates using `__validation_model__` (full validation)

If Pydantic raises `ValidationError`, it is caught and:
- If the underlying cause is an `InvarianceException`, that exception is re-raised directly
- Otherwise, a `ModelValidationError(DomainException)` is raised wrapping the original error

After validation, calls `__set_model_attributes(validated)` to copy fields and private attributes onto `self` using `object.__setattr__`.

### `__set_model_attributes(validated)`
Copies all fields from `validated.model_dump()` plus `__pydantic_private__` attributes onto `self` using `object.__setattr__`.

### `__post_init__()`
Empty hook method. Called from `BaseValidator.__init__` after `__set_model_attributes`. Only runs on normal `__init__` (not during `reconstruct` — guarded by `_use_raw_model` check). Override in subclasses to run custom logic after field initialization.

### `__repr__()`
Generates repr based on `__validation_model__.model_fields` keys.

## ReconstructMixin

`ReconstructMixin` (in `reconstructable.py`) provides the `reconstruct(**kwargs) -> Self` classmethod:

1. Sets `_use_raw_model` ContextVar to `True`
2. Calls `cls(**kwargs)` — goes through `__init__` but with the raw model
3. Resets the ContextVar

This bypasses `@field_invariance`, `@invariance`, and any `Annotated` constraints/validators.
Only classes that mix in `ReconstructMixin` have `reconstruct()`:
- `Entity(ReconstructMixin, BaseGuarded)` — has reconstruct
- `ValueObject(ReconstructMixin, BaseSealed)` — has reconstruct
- `Service(BaseSealed)` — does NOT have reconstruct
- `UseCase(BaseSealed)` — does NOT have reconstruct

## Internal State

- `_use_raw_model: ContextVar[bool]` — module-level (in `base_validator.py`), controls model selection in `__init__`. Used by both `BaseValidator.__init__` and `ReconstructMixin.reconstruct()`.
- `VALIDATION_MODEL_KEY = "__validation_model__"` — attribute name for the validation model
- `RAW_MODEL_KEY = "__raw_model__"` — attribute name for the raw model

## Dependencies

- `pydantic.BaseModel`
- `model_maker` (make_validation_model, make_raw_model)
- `fields.Field`
