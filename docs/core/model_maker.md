# ModelMaker — Dual Pydantic Model Generation

## Purpose

On-the-fly generation of two Pydantic `BaseModel` subclasses for every user class.

## Key Constants

- `VALIDATION_MODEL_KEY = "__validation_model__"` — attribute name on the user class
- `RAW_MODEL_KEY = "__raw_model__"` — attribute name on the user class

## Functions

### `get_parent_models(bases, key) -> tuple[Type[BaseModel], ...]`
Collects parent models from the bases by looking up `key` (e.g., `__validation_model__`). Falls back to `(BaseModel,)` if no bases have the attribute.

### `get_model_config(cls) -> ConfigDict`
Returns a `ConfigDict(arbitrary_types_allowed=True)`, preserving any existing `model_config` on the class.

### `make_validation_model(cls, name, bases) -> Type[BaseModel]`
Builds a Pydantic model that includes:
- All annotations from the user class
- Default values
- `@field_invariance` methods (detected via `is_validator()`)
- `@invariance` methods (detected via `is_validator()`)
- Parent validation models from MRO

### `strip_validators(annotation)`
If the annotation is `Annotated[T, ...]`, returns just `T`. Otherwise returns the annotation unchanged.

### `make_raw_model(cls, name, bases) -> Type[BaseModel]`
Builds a Pydantic model with:
- All annotations **stripped of validators** via `strip_validators()`
- `ModelPrivateAttr` fields preserved (for private fields)
- No `@field_invariance` or `@invariance` methods
- Parent raw models from MRO

## Flow

```
@dataclass_transform
class User(BaseValidator):
    age: int
    name: Annotated[str, Field(min_length=3)]

    @field_invariance("age")
    def normalize_age(cls, value): ...

    @invariance
    def check(self): ...
```

Creates:

```python
class UserValidationModel(BaseModel):
    age: int
    name: str  # with Field(min_length=3)

    @field_validator("age")
    def normalize_age(cls, value): ...  # Pydantic-wrapped

    @model_validator(mode="after")
    def check(self): ...  # Pydantic-wrapped

class UserRawModel(BaseModel):
    age: int
    name: str  # NO min_length constraint, no Annotated

    # NO validators, NO invariance methods
```
