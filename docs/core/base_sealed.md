# BaseSealed

## Purpose

Truly immutable domain objects. Blocks ALL mutation after construction, including via `__mutate__(inherit_mutate=True)`.

## Implementation

`BaseSealed` overrides `_mutation_status` to always return `MutatingState.BLOCK` once the object is initialized (and `MutatingState.INHERIT` during `__post_init__`, so default factories on `init=False` fields can still run). This guarantees that `_is_mutation_allowed` evaluates to `False` regardless of the underlying `__mutating_context__` state.

The class does not need a custom `MutatingContext` subclass; the default `MutatingContext` is inherited from `BaseGuarded` but ignored after the override.

## BaseSealed(BaseGuarded)

### `__init__(**kwargs)`
No override needed — the class-level `__skip_method_wrapping__` and the `_mutation_status` override are enough.

### `_can_mutate() -> bool`
Always returns `False`. Belt and suspenders: even if a future change to `_mutation_status` accidentally exposed `PASS`, `_can_mutate()` would still veto the mutation.

### `_mutation_status` property
Returns `INHERIT` if `not _is_initialized`, else `BLOCK`. This is what makes `__mutate__(inherit_mutate=True)` a no-op for sealed instances: `enter(INHERIT)` is called on the underlying `MutatingContext`, but `_mutation_status` ignores it.

### Class variables
- `__skip_method_wrapping__ = True` — tells `__init_subclass__` to stop method wrapping at this class

## Inheritance

```
BaseValidator (ValidationModelMeta)
  └── BaseGuarded
        └── BaseSealed
```

## Used by
- `Event(BaseSealed)` — events are immutable
- `ValueObject(BaseSealed)` — DDD value objects are immutable
- `Service(BaseSealed)` — DDD services are stateless and immutable
