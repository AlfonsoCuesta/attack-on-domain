# BaseGuarded

## Purpose

`BaseGuarded` provides mutable domain objects with controlled mutation semantics. Public methods are auto-wrapped with a mutation context via `__init_subclass__`. Attributes are protected via `__setattr__`/`__getattribute__` overrides.

## Method Wrapping via `__init_subclass__`

`BaseGuarded.__init_subclass__` calls `_wrap_public_methods(cls)` (module-level function) whenever a subclass is created. This replaces the old `GuardedBaseMeta` metaclass.

### `_wrap_public_methods(cls)`

1. Traverses the MRO from most-derived to most-base (the order returned by `cls.__mro__`)
2. For each class, iterates its `__dict__` and wraps eligible methods with `mutate()`
3. Stops at any class with `__skip_method_wrapping__ = True`

### Method eligibility
A method IS wrapped if all of these are true:
- It IS a function (`inspect.isfunction`)
- It is NOT a dunder (name starts and ends with `__`, length > 4)
- It is NOT a bound method (`inspect.ismethod`)
- It does NOT have `__field_validator_info__` (not a validator)
- It does NOT have `__mutable__` (not already explicitly marked)
- It does NOT have `__isabstractmethod__` (abstract methods are skipped)

### INHERIT state propagation
If a method overrides a parent method that was marked as `INHERIT`, the override also gets `INHERIT` status.

## BaseGuarded

### Class Variables
- `__mutating_context_class__` — defaults to `MutatingContext`
- `__skip_method_wrapping__` — defaults to `True`; when `True`, `__init_subclass__` stops wrapping methods at this class in the MRO

### `__init__(**kwargs)`
1. Creates `__mutating_context__` via `object.__setattr__` (bypasses the guard) from `__mutating_context_class__`
2. Enters `INHERIT` context (allows mutation during `__post_init__`)
3. Calls `super().__init__(**kwargs)` (which runs `BaseValidator.__init__` → sets fields → calls `__post_init__()`)
4. Exits `INHERIT` context

Because `__mutating_context__` is created before `super().__init__()`, the mutation context is available during `__post_init__`. The `_event_emitter` is set by Pydantic in `__set_model_attributes` before `__post_init__` runs.

### Mutation Control
- `_can_mutate() -> bool` — override this in subclasses. Default returns `True`. Decorated with `@inherit_context`.
- `_mutation_status` property — returns `self.__mutating_context__.status` (the context is the single source of truth)
- `__mutate__(inherit_mutate=False)` — context manager that enters/exits the mutating context with the appropriate state
- `_is_mutation_allowed` property — `BLOCK` → `False`, `INHERIT` → `True`, `PASS` → delegates to `_can_mutate()`

### `__setattr__(name, value)`
Raises `MutationForbiddenException` if `_is_mutation_allowed` is `False`.

### `__delattr__(name)`
Raises `MutationForbiddenException` if `_is_mutation_allowed` is `False`.

### `__getattribute__(name)`
For model fields (non-function, non-private, non-dunder):
- If mutation is NOT allowed → returns `make_immutable(value)` (wraps in immutable proxy)
- If mutation IS allowed → returns the raw value

This is what makes complex field protection work: when you're outside a mutation method, reading `self.items` returns an `ImmutableList` instead of a plain `list`.

## Decorators

### `mutate(fn, inherit_mutate=False)`
Wraps a function such that calling it enters a mutation context (`PASS` normally, `INHERIT` if `inherit_mutate=True`). The wrapper is marked with `__mutable__`.

### `inherit_context(fn)`
Shorthand for `mutate(fn, inherit_mutate=True)`. Allows mutation even when `_can_mutate()` returns `False`.
