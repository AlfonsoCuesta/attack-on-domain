# deedee

Helpers for **domain-driven design** in Python: entities, value objects, bounded contexts, domain events, and Pydantic v2–based validation.

## Install

```bash
pip install deedee-domain
```

With **uv** in another project (adds the dependency to that project’s `pyproject.toml`):

```bash
uv add deedee-domain
```

Or install into the active environment without editing a project file:

```bash
uv pip install deedee-domain
```

The installed module is still named `deedee`, so imports do not change.

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
