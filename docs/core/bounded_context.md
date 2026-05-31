# BoundedContext

## Purpose

Assembles a Domain-Driven Design bounded context by collecting aggregate roots, entities, value objects, and services. Validates type constraints at construction time.

## Constructor

```python
class BoundedContext:
    def __init__(
        self,
        aggregate_roots: Optional[Iterable[RootEntityType]] = None,
        services: Optional[Iterable[ServiceType]] = None,
    ):
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `aggregate_roots` | `Optional[Iterable[type[RootEntity]]]` | Root entity classes in this context |
| `services` | `Optional[Iterable[type[Service]]]` | Service classes in this context |

### Validation

1. Each item in `aggregate_roots` must be:
   - A class (raises `ClassExpectedError` if not)
   - A subclass of `Entity` (raises `InvalidEntityTypeError` if not)
   - A root entity (`issubclass(item, RootEntity)` is True, raises `InvalidRootEntityTypeError` if not)

2. Each item in `services` must be:
   - A class (raises `ClassExpectedError` if not)
   - A subclass of `Service` (raises `InvalidServiceTypeError` if not)

## Type Discovery: `_discover_types()`

After validation, `_discover_types()` recursively finds all entities and value objects:

```
Input: [Order] (RootEntity)
  ↓ get_type_hints(Order)
  ↓ extract_types_from_annotation for each field
  ↓
  Found: LineItem (Entity) → recurse
         Address (ValueObject) → recurse
            Found: City (ValueObject) → recurse
                   Country (ValueObject) → recurse
  ↓
Output: entities=[LineItem], value_objects=[Address, City, Country]
```

## Type Checks

After discovery, checks run on all discovered types:

| Function | Target | Check |
|----------|--------|-------|
| `check_root_entity` | All entities (roots + discovered) | No field references RootEntity |
| `check_value_object` | All discovered value objects | No field references Entity or RootEntity |
| `check_service` | All services | No param or return type is non-root Entity |

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `aggregate_roots` | `tuple[type[RootEntity], ...]` | Root entities |
| `entities` | `tuple[type[Entity], ...]` | Non-root entities (auto-discovered) |
| `value_objects` | `tuple[type[ValueObject], ...]` | Value objects (auto-discovered) |
| `services` | `tuple[type[Service], ...]` | Services |

## Usage

```python
class Order(RootEntity):
    id: int
    lines: list[OrderLine]

class OrderLine(Entity):
    id: int
    product: str

class ShippingService(Service):
    def ship(self, order: Order) -> None:
        pass

ctx = BoundedContext(
    aggregate_roots=[Order],
    services=[ShippingService],
)

assert Order in ctx.aggregate_roots
assert OrderLine in ctx.entities
assert ShippingService in ctx.services
```
