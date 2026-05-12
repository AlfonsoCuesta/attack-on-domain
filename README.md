# deedee

Helpers for **domain-driven design** in Python: entities, value objects, bounded contexts, domain events, and Pydantic v2–based validation.

## Install

```bash
pip install deedee
```

## Usage

Import only from the top-level package:

```python
from deedee import (
    BoundedContext,
    DomainEvent,
    DomainException,
    Entity,
    ValueObject,
)
```

Requires **Python 3.14+**.
