# Type Checking System

## Purpose

Enforces DDD type constraints at `BoundedContext` construction time. Lives in `code/aod/_internal/core/type_checking/`.

## Package Structure

```
type_checking/
├── __init__.py       # Re-exports: extract_types_from_annotation, check_entity, check_root_entity, check_value_object, check_service
├── extractors.py     # extract_types_from_annotation, get_validation_model
└── checks.py         # check_entity, check_root_entity, check_value_object, check_service
```

## extractors.py

### `extract_types_from_annotation(annotation: object) -> list[type]`

Recursively extracts all type objects from an annotation, handling:
- Plain types (`int`, `str`, `User`) → `[type]`
- `Annotated[T, ...]` → recurses on `T`
- `Optional[T]`, `Union[A, B]` → recurses on each arg, filters out `NoneType`
- `list[T]`, `dict[K, V]`, etc. → recurses on each type arg
- Forward references (strings) → returns empty `[]`

### `get_validation_model(cls: type) -> type[BaseModel]`

Returns `cls.__validation_model__`. Only call on `BaseValidator` subclasses.

## checks.py

### `check_entity(entity_cls: type)`

Raises `InvalidNestedTypeError` if any field of `entity_cls` references `RootEntity` or a subclass of it.

### `check_root_entity(root_entity_cls: type)`

Delegates to `check_entity`. (Same constraint — RootEntities cannot contain RootEntity fields.)

### `check_value_object(vo_cls: type)`

Raises `InvalidNestedTypeError` if any field references `Entity` (including `RootEntity`).

**Allowed**: primitives, str, ValueObjects
**Forbidden**: Entity, RootEntity (and subclasses)

### `check_service(service_cls: type)`

For each public method (non-dunder, non-private) of `service_cls`:

1. Inspects parameters via `inspect.signature`
2. Resolves forward references via `_resolve_annotation` (uses `typing.get_type_hints`)
3. Inspects return type via `signature.return_annotation`
4. Calls `_is_entity_param()` for each parameter and return type

Raises `InvalidServiceParameterError` if any param or return type is a non-root `Entity`.

**Allowed**: custom classes, `RootEntity`, `ValueObject`
**Forbidden**: non-root `Entity`

### Helper: `_is_entity_param(annotation, entity, root_entity)`

Extracts types from annotation via `extract_types_from_annotation`. Returns `True` if any type is a subclass of `entity` but NOT a subclass of `root_entity`.

### Helper: `_references_base(annotation, *bases)`

Extracts types from annotation. Returns `True` if any type is a subclass of any of the given bases.

## Exceptions

- `InvalidNestedTypeError` — raised by `check_entity`, `check_root_entity`, `check_value_object`
- `InvalidServiceParameterError` — raised by `check_service`
