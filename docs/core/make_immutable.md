# MakeImmutable System

## Purpose

When `BaseGuarded.__getattribute__` detects mutation is not allowed, it wraps the returned value in an immutable proxy. This system creates those proxies.

## Entry Point: `make_immutable(value)`

Dispatch logic:
1. **Primitives** (`int`, `float`, `str`, `bool`, `bytes`, `None`, `datetime.*`, `decimal.Decimal`, `uuid.UUID`) → returned as-is
2. **Callables** (functions, methods, builtins) → returned as-is
3. **Already immutable** (`ImmutableList`, `ImmutableDict`, `ImmutableSet`, `frozenset`, anything with `__immutable_class__`) → returned as-is
4. **list** → `ImmutableList(value, make_immutable)`
5. **dict** → `ImmutableDict(value, make_immutable)`
6. **set** → `ImmutableSet(value, make_immutable)`
7. **Everything else** → `_make_immutable_object(value, make_immutable)` (dynamic proxy)

## ImmutableList(list)

Subclass of `list` that blocks all mutating operations:
- `append`, `extend`, `insert`, `remove`, `pop`, `clear`, `sort`, `reverse`
- `__setitem__`, `__delitem__`, `__iadd__`, `__imul__`

Reading methods (`__getitem__`, `__iter__`) wrap returned values via the factory.

## ImmutableDict(dict)

Blocks: `__setitem__`, `__delitem__`, `update`, `pop`, `popitem`, `clear`, `setdefault`

Reading methods (`__getitem__`, `iter`, `get`, `items`, `keys`, `values`) wrap returned values.

## ImmutableSet(set)

Blocks: `add`, `discard`, `remove`, `pop`, `clear`, `update`, `__ior__`, `__iand__`, `__ixor__`, `__isub__`

`__iter__` wraps yielded items.

## Dynamic Custom Object Proxy: `Immutable{ClassName}`

Created by `_make_immutable_object()` in `immutable_custom.py`:

1. Checks cache (`_immutable_cache`) — if a class was already generated for this type, reuse it
2. Creates `class Immutable{ClassName}(ClassName)` dynamically via `type()`
3. Overrides `__getattribute__` — non-dunder attribute access wraps the value via factory; dunders go to `get_wrapped_methods()`
4. Sets `__wrapped_object__` to the original instance
5. Copies state from original (`__dict__` + `__slots__`)
6. Caches the generated class

### Dunder Method Handling (`wrapped_methods.py`)

- **Safe dunders** (comparison, conversion, container, numeric): auto-generated methods that delegate to the wrapped object and wrap results
- **Mutating dunders** (`__setattr__`, `__delattr__`, `__setitem__`, `__delitem__`, `__iadd__`, etc.): auto-generated methods that raise `MutationForbiddenException`
- Only generates methods that the original class actually defines (checks MRO)
