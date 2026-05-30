# BaseMutable & MutableBaseMeta

## Purpose

`BaseMutable` provides mutable domain objects with controlled mutation semantics. It auto-wraps public methods with a mutation context and protects attributes via `__setattr__`/`__getattribute__` overrides.

## MutableBaseMeta (metaclass)

Extends `PydanticFacadeMeta`. After class creation, it:

1. Traverses the MRO in reverse (from most-base to most-derived)
2. For each class, iterates its `__dict__` and wraps eligible methods with `mutate()`
3. Stops at any class with `__stop_context_mutating__ = True`

### Method eligibility
A method IS wrapped if all of these are true:
- It IS a function (`inspect.isfunction`)
- It is NOT a dunder (`is_dunder()` → name starts with `__`)
- It is NOT a bound method (`inspect.ismethod`)
- It does NOT have `__field_validator_info__` (not a validator)
- It does NOT have `__mutable__` (not already explicitly marked)

### SUPER state propagation
If a method overrides a parent method that was marked as `SUPER`, the override also gets `SUPER` status.

## BaseMutable

### Class Variables
- `__mutating_context_class__` — defaults to `MutatingContext`
- `__stop_context_mutating__` — defaults to `True`; when `True`, `MutableBaseMeta` stops wrapping methods at this class in the MRO

### `__init__(**kwargs)`
1. Calls `super().__init__(**kwargs)` (which runs `BaseValidator.__init__`)
2. Creates a new `MutatingContext` instance as `self.__mutating_context__`
3. Calls `self.__post_init__()` **only if** `_use_raw_model` is `False` (i.e., not from `from_existing`)
4. Sets `self.__initialized__ = True`

Because `__post_init__` runs after `__mutating_context__` exists but before `__initialized__`, public methods can be called and field mutation is allowed during the hook. The `_event_emitter` must be created before `super().__init__()` for it to be available in the hook (Entity and ValueObject already do this).

### Mutation Control
- `_can_mutate() -> bool` — override this in subclasses. Default returns `True`. Decorated with `@super_context`.
- `_mutation_status` property — returns `SUPER` if `not _is_initialized`, delegates to `__mutating_context__.status` otherwise
- `__mutate__(super_mutate=False)` — context manager that enters/exits the mutating context with the appropriate state
- `_is_mutation_allowed` property — `BLOCK` → `False`, `SUPER` → `True`, `PASS` → delegates to `_can_mutate()`

### `__setattr__(name, value)`
Raises `MutationForbiddenException` if `_is_mutation_allowed` is `False`.

### `__getattribute__(name)`
For model fields (non-function, non-private, non-dunder):
- If mutation is NOT allowed → returns `make_immutable(value)` (wraps in immutable proxy)
- If mutation IS allowed → returns the raw value

This is what makes complex field protection work: when you're outside a mutation method, reading `self.items` returns an `ImmutableList` instead of a plain `list`.

## Decorators

### `mutate(fn, super_mutate=False)`
Wraps a function such that calling it enters a mutation context (`PASS` normally, `SUPER` if `super_mutate=True`). The wrapper is marked with `__mutable__`.

### `super_context(fn)`
Shorthand for `mutate(fn, super_mutate=True)`. Allows mutation even when `_can_mutate()` returns `False`.
