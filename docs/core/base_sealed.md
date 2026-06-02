# BaseSealed

## Purpose

Truly immutable domain objects. Blocks ALL mutation after construction, including via `__mutate__()`.

## Implementation

`BaseSealed` overrides `_mutation_status` to return `INHERIT` during init (the context status) and `BLOCK` for everything else (including `PASS`). This guarantees that `_is_mutation_allowed` evaluates to `False` regardless of the underlying `__mutating_context__` state, except during init.

## BaseSealed(BaseGuarded)

### `_can_mutate() -> bool`
Always returns `False`. Belt and suspenders: even if a future change to `_mutation_status` accidentally exposed `PASS`, `_can_mutate()` would still veto the mutation.

### `_mutation_status` property
Returns `self.__mutating_context__.status` if `INHERIT`, otherwise `BLOCK`. This means:
- During `__init__`: context is `INHERIT` → returns `INHERIT` → mutation allowed
- Inside a public method: context is `PASS` → returns `BLOCK` → mutation blocked
- From outside: context is `BLOCK` → returns `BLOCK` → mutation blocked

### Class variables
- `__skip_method_wrapping__ = True` — tells `__init_subclass__` to stop method wrapping at this class (but `@inherit_context` on parent methods is still picked up via `super_attrs`)

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
- `UseCase(BaseSealed)` — application use cases (mutation only inside `run()` via `@inherit_context`, which uses `INHERIT` context and bypasses the seal)
