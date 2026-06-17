# Domain-Driven Design Concepts

This page explains the core DDD concepts — pure theory with no framework specifics.

## What Is DDD?

Domain-Driven Design (DDD) is an approach to software development that focuses on:

1. **Putting the business domain first** — the code reflects how the business works, not the technology
2. **Using a shared language** — developers and domain experts speak the same language (Ubiquitous Language), with terms defined in code
3. **Creating clear boundaries** — different parts of the system map to distinct business subdomains, each with its own model

The goal is software that remains understandable and maintainable as business complexity grows.

## The Building Blocks

### Value Object

Immutable object defined by its attributes, not its identity.

**Characteristics:**
- No identity field
- Compared by value (all fields must match)
- Cannot be mutated after creation
- Can contain other Value Objects
- Examples: Money, Email, Address, DateRange

**Best practices:**
- Make them immutable — any "change" produces a new instance
- Keep them small and self-validating
- Use them to wrap primitive types that have business meaning (e.g. `Email` instead of `str`)

### Entity

Mutable object with a distinct identity that persists over time.

**Characteristics:**
- Has an identity field (typically `id`)
- Can change state through public methods
- Compared by identity, not by value — two entities with the same `id` are the same entity regardless of other attributes
- Lives across multiple transactions

**Best practices:**
- Protect invariants inside public methods — validate before mutating
- Expose behaviour, not data (tell an entity what to do, don't ask for its data and do it externally)
- Keep identity simple (string, UUID, or a dedicated Value Object)

### Aggregate and Aggregate Root

An **aggregate** is a cluster of associated objects treated as a single unit for data changes. The **aggregate root** is the only object that external code references directly.

**Characteristics:**
- The aggregate root is an Entity
- External objects reference the aggregate by its root's identity, never by object reference
- All invariants are enforced by the root
- Child entities exist only inside the aggregate boundary

**Best practices:**
- Keep aggregates small — only include what must be consistent together
- Reference other aggregates by identity, not by object reference
- One transaction = one aggregate (don't modify multiple aggregates in a single transaction)
- Load the entire aggregate when you need to modify it

### Domain Service

Stateless operation that does not naturally belong to an Entity or Value Object.

**When to use:**
- The operation involves multiple aggregates
- The operation requires external data (pricing from an API, tax rates from a database)
- The logic does not fit naturally inside a single entity

**Best practices:**
- Keep services stateless — all dependencies are passed in or injected
- Name them after the business activity they perform
- A service should not replace what should be an entity method

### Domain Event

A record of something significant that happened in the domain.

**Characteristics:**
- Immutable and timestamped
- Named in the past tense (e.g. `OrderPlaced`, `UserRegistered`)
- Represents a fact that other parts of the system can react to

**Best practices:**
- Events decouple aggregates — one aggregate emits, another reacts
- Store events for audit trails and event sourcing
- Keep events small — include only what happened, not why

### Domain Invariant

A business rule that must always be true for the model to be consistent.

**Examples:**
- An order total cannot be negative
- A booking cannot overlap with another booking for the same resource
- An email address must be valid format

**Best practices:**
- Enforce invariants at construction time and on every state change
- Put invariants closest to the data they protect (in the Entity or Value Object that owns the data)
- Throw meaningful exceptions when invariants are violated

### Bounded Context

A boundary within which a particular domain model is defined and consistent.

**Characteristics:**
- Each context has its own Ubiquitous Language
- The same term can mean different things in different contexts
- Contexts communicate through events or anti-corruption layers

**Best practices:**
- Define context boundaries based on business subdomains, not technical layers
- A typical application has 3-7 bounded contexts
- Keep the model pure inside a context — don't import models from other contexts

## Architectural Patterns

### Layered Architecture

DDD organises code into concentric layers where each layer depends only on the one below it:

| Layer | Responsibility | Depends On |
|-------|---------------|------------|
| **Infrastructure** | Technical concerns: databases, APIs, message queues | Application |
| **Application** | Orchestration, transactions, security | Domain |
| **Domain** | Business logic, rules, models | None (pure) |

The **Domain layer** contains only business logic with no framework or infrastructure dependencies. The **Application layer** coordinates domain objects and defines ports. The **Infrastructure layer** implements those ports for databases, APIs, and other external systems.

### Ports and Adapters (Hexagonal Architecture)

Also known as the hexagonal architecture, this pattern places the domain and application at the centre, with ports defining interfaces and adapters providing implementations:

- **Port** — An interface that defines how the core interacts with the outside world (e.g. "save an order")
- **Adapter** — A concrete implementation of that port (e.g. "save an order to PostgreSQL")
- **Driving adapters** — Initiate the flow (controllers, CLI, tests)
- **Driven adapters** — Are called by the core (database, message queue, API)

The rule: the core depends on ports, not on adapters. You can swap adapters without changing business logic.

### CQRS (Command Query Responsibility Segregation)

Separation of write and read models:

- **Commands** — Requests that change state (writes). Return minimal data (typically void or a success indicator)
- **Queries** — Requests that return data (reads). Do not modify state

**Benefits:**
- Read and write models can be optimised independently (different databases, different schemas)
- Commands can validate against the full domain model; queries can return flat, denormalised data
- Security rules differ for writes vs reads

**Best practices:**
- Commands are named imperatively (`PlaceOrder`, `CreateUser`)
- Queries are named descriptively (`GetOrder`, `FindUsersByName`)
- Handlers for commands and queries are separate — a command handler should not return query data
- Commands use the domain model (Entities, Value Objects, invariants); queries can bypass it for performance

### Transactions

A transaction groups multiple operations into a single unit that either succeeds completely or fails completely.

**Best practices in DDD:**
- One transaction per aggregate — never modify two aggregates in the same transaction
- Use optimistic concurrency for long-running operations
- Use eventual consistency between bounded contexts (events)
- The application layer manages transaction boundaries, not the domain

## Summary of Key Principles

| Principle | Description |
|-----------|-------------|
| **Ubiquitous Language** | Use the same terms in code, conversations, and documentation |
| **Persistence Ignorance** | Domain objects do not know about databases, ORMs, or serialisation |
| **Aggregate Consistency** | One transaction per aggregate; enforce invariants at the root |
| **Separation of Concerns** | Domain, Application, and Infrastructure have distinct responsibilities |
| **Dependency Inversion** | Core depends on ports (interfaces), not concrete adapters |
| **Command-Query Separation** | Do not mix state-changing and state-reading operations |

## Next Steps

<div class="home-features">

<div class="feature-card">
<h3><a href="installation.md">Installation</a></h3>
<p>Install the library</p>
</div>

<div class="feature-card">
<h3><a href="quickstart.md">Quick Start</a></h3>
<p>Apply these concepts in a working example</p>
</div>

<div class="feature-card">
<h3><a href="mapping.md">Mapping DDD to AoD</a></h3>
<p>See how each concept translates to code</p>
</div>

</div>