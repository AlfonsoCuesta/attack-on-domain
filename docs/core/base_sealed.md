# BaseSealed

## Purpose

Truly immutable domain objects. Blocks ALL mutation after construction.

## MutatingContextBlock

A `MutatingContext` subclass that always reports `BLOCK` status. `enter()` and `exit()` are no-ops — the context never allows anything.

## BaseSealed(BaseGuarded)

### `__init__(**kwargs)`
1. Calls `super().__init__(**kwargs)` (which runs `BaseGuarded.__init__` → `BaseValidator.__init__`)
2. Replaces the mutating context with `MutatingContextBlock` via `object.__setattr__`

### `_can_mutate() -> bool`
Always returns `False`.

### Class variables
- `__stop_context_mutating__ = True` — tells `GuardedBaseMeta` to stop method wrapping at this class

## Inheritance

```
BaseValidator
  └── BaseGuarded (GuardedBaseMeta)
        └── BaseSealed
```

## Used by
- `Event(BaseSealed)` — events are immutable
- `ValueObject(BaseSealed)` — DDD value objects are immutable
