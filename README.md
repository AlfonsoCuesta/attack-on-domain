# attack-on-domain

Helpers for **domain-driven design** in Python: entities, value objects, bounded contexts, domain events, and Pydantic v2–based validation.

## Install

```bash
pip install attack-on-domain
```

With **uv** in another project:

```bash
uv add attack-on-domain
```

Or install into the active environment:

```bash
uv pip install attack-on-domain
```

## Usage

Import only from the public API:

```python
from aod.domain import (
    BoundedContext,
    Entity,
    ValueObject,
)
from aod.domain import DomainException
from aod.events import Event
```

Requires **Python 3.14+**.
