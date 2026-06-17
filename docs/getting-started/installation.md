# Installation

## Requirements

- Python 3.14 or later
- Pydantic v2 (automatically installed)

## Install

```bash
pip install attack-on-domain
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add attack-on-domain
```

## Verify

```python
import aod
print(aod.__version__)
```

## Dependencies

`attack-on-domain` requires:

- `pydantic>=2.12.4` — Core validation and serialization
- `polyfactory>=3.3.0` — Test data generation
- `typing-inspect>=0.9.0` — Type inspection utilities

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="quickstart.md">Quick Start</a></h3>
<p>Build your first domain in 5 minutes</p>
</div>

<div class="feature-card">
<h3><a href="concepts.md">DDD Concepts</a></h3>
<p>Learn the theory behind Domain-Driven Design</p>
</div>

</div>