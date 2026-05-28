# BaseImmutable

## Purpose

Truly immutable domain objects. Blocks ALL mutation after construction.

## MutatingContextBlock

A `MutatingContext` subclass that always reports `BLOCK` status. `enter()` and `exit()` are no-ops — the context never allows anything.

## BaseImmutable(BaseMutable)

### `__init__(**kwargs)`
1. Calls `super().__init__(**kwargs)` (which runs `BaseMutable.__init__` → `BaseValidator.__init__`)
2. Replaces the mutating context with `MutatingContextBlock` via `object.__setattr__`

### `_can_mutate() -> bool`
Always returns `False`.

### Class variables
- `__stop_context_mutating__ = True` — tells `MutableBaseMeta` to stop method wrapping at this class

## Inheritance

```
BaseValidator
  └── BaseMutable (MutableBaseMeta)
        └── BaseImmutable
```

## Used by
- `Event(BaseImmutable)` — events are immutable
- `ValueObject(BaseImmutable)` — DDD value objects are immutable
