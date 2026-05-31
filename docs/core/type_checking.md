# Type Checking System

## Purpose

Enforces DDD type constraints at `BoundedContext` construction time. Lives in `code/aod/_internal/core/type_handlers/`.

## Package Structure

```
type_checking/
├── __init__.py       # Re-exports: extract_types_from_annotation, get_validation_model
└── extractors.py     # extract_types_from_annotation, get_validation_model, extract_domain_types_from_model

type_handlers/
├── __init__.py                    # Re-exports: BaseGuardedTypeHandler, ServiceTypeHandler
├── base_guarded_handler.py        # check_entity, check_root_entity, check_value_object, discover_types
└── service_handler.py             # check_service
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

## base_guarded_handler.py

### `check_entity(entity_cls: type[Entity])`

Raises `InvalidNestedTypeError` if any field of `entity_cls` references `RootEntity` or a subclass of it.

### `check_root_entity(root_entity_cls: type[Entity])`

Delegates to `check_entity`. (Same constraint — RootEntities cannot contain RootEntity fields.)

### `check_value_object(vo_cls: type[ValueObject])`

Raises `InvalidNestedTypeError` if any field references `Entity` (including `RootEntity`).

**Allowed**: primitives, str, ValueObjects
**Forbidden**: Entity, RootEntity (and subclasses)

### `discover_types(root_entities) -> (entities, value_objects)`

Recursively traverses field type hints starting from root entities to discover all Entity and ValueObject types referenced in the aggregate.

## service_handler.py

### `check_service(service_cls: type[Service])`

For each public method (non-dunder, non-private) of `service_cls`:

1. Inspects parameters via `inspect.signature`
2. Resolves forward references via `_resolve_annotation` (uses `typing.get_type_hints`)
3. Inspects return type via `signature.return_annotation`
4. Calls `_is_entity_param()` for each parameter and return type

Raises `InvalidServiceParameterError` if any param or return type is a non-root `Entity`.

**Allowed in services**: custom classes, `RootEntity`, `ValueObject`
**Forbidden in services**: non-root `Entity`

## Exceptions

- `InvalidNestedTypeError` — raised by `check_entity`, `check_root_entity`, `check_value_object`
- `InvalidServiceParameterError` — raised by `check_service`
