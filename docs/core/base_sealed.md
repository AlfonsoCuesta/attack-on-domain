# BaseSealed

## Purpose

Truly immutable domain objects. Blocks ALL mutation after construction.

## MutatingContextBlock

A `MutatingContext` subclass that always reports `BLOCK` status. `enter()` and `exit()` are no-ops — the context never allows anything.

## BaseSealed(BaseGuarded)

### `__init__(**kwargs)`
No override needed — `__mutating_context_class__` is set as a ClassVar at the class level, so `BaseGuarded.__init__` creates the correct `MutatingContextBlock` from the start. This fixes a bug where the old `BaseSealed.__init__` set it after `super().__init__()`.

### `_can_mutate() -> bool`
Always returns `False`.

### Class variables
- `__mutating_context_class__` — set to `MutatingContextBlock` (ClassVar override)
- `__stop_context_mutating__ = True` — tells `__init_subclass__` to stop method wrapping at this class

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
