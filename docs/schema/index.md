---
hide:
  - navigation
  - toc
---

# Schema

The schema system provides introspection and documentation generation for your DDD application.

## Overview

Schema classes analyze your domain model and generate documentation:

- **App** — aggregates modules, validates no duplicate types across bounded contexts
- **BoundedContext** — discovers entities, value objects, services from aggregate roots
- **Infrastructure** — validates handler-port wiring, extracts sessions
- **Module** — validates that every contract has a handler and every port has an implementation
- **AutoDoc** — generates a complete zensical documentation site from your App

## Consistency Checks

All schema classes enforce consistency at construction time:

| Class | Validates |
|-------|-----------|
| `App` | No duplicate domain types across modules |
| `BoundedContext` | Only `RootEntity` as aggregate roots, only `Service` as services |
| `Module` | Every contract has a handler, every port has an implementation |
| `Infrastructure` | No duplicate contracts across handlers |

## Quick Start

```python
from aod.schema import App, BoundedContext, Infrastructure, Module

bc = BoundedContext(
    aggregate_roots=[Order],
    use_cases=[OrderUseCase],
    name="Orders",
)

infra = Infrastructure(
    handlers=[PlaceOrderHandler, GetOrderHandler],
    ports=[SmtpSender],
)

mod = Module(name="orders", context=bc, infrastructure=infra)
app = App(name="MyApp", modules=[mod])
```

## AutoDoc

AutoDoc generates a complete zensical documentation site from your App.

### Usage

```python
from aod._internal.schema import AutoDoc

doc = AutoDoc(
    app,
    output_dir="my-site",
    site_name="MyApp Docs",
    site_description="DDD documentation",
    repo_url="https://github.com/example/myapp",
)

doc.generate()
# Then: cd my-site && uv run zensical build --clean
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `app` | `App` | The application schema to document |
| `output_dir` | `str \| Path` | Directory for generated files |
| `site_name` | `str` | Site name (defaults to `app.name`) |
| `site_description` | `str` | Site description (defaults to `app.description`) |
| `repo_url` | `str` | Repository URL for edit links |
| `repo_name` | `str` | Repository name (defaults to `app.name`) |
| `edit_uri` | `str` | Edit URI template |

### Generated Structure

```
my-site/
├── zensical.toml
├── docs/
│   ├── index.md
│   ├── stylesheets/extra.css
│   ├── overrides/main.html
│   └── bounded-contexts/
│       ├── {module-name}/
│       │   ├── index.md
│       │   ├── glossary.md
│       │   ├── entities.md
│       │   └── infrastructure.md
```

### Features

- **Home page** — app description with cards linking to each bounded context
- **Navigation** — tabs for Home, then each bounded context as a top-level item
- **Glossary** — all domain terms with descriptions
- **Entities** — root entities, entities, value objects, services with fields and methods
- **Infrastructure** — handlers, sessions, ports, projections
- **Use Cases** — use cases with ports and parameters
- **Projections** — read/write projections with methods

### Custom Assets

Place your own files in the output directory before calling `generate()`:

```python
# Add custom CSS
Path("my-site/docs/stylesheets/extra.css").write_text("/* custom */")

# Add logos
Path("my-site/img/logo.png").write_bytes(logo_bytes)

# Generate — preserves your files
doc.generate()
```

### Example

Run the example script to see AutoDoc in action:

```bash
uv run python code/tests/schema/make_example_site.py
cd code/tests/schema/example-site
uv run zensical build --clean
```

## Zensical

AutoDoc generates sites compatible with [zensical](https://github.com/nicholasgasior/zensical), a mkdocs-material-compatible static site generator. For more information on zensical features and configuration, see the [zensical documentation](https://github.com/nicholasgasior/zensical#readme).