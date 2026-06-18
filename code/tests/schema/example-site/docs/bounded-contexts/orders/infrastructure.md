---
hide:
  - navigation
  - toc
---

# Orders — Infrastructure

## Handlers

### PlaceOrderHandler

- **Type:** `CommandHandler`
- **Contract:** `PlaceOrder`
- **Session:** `PostgresSession`

**Handle method:**

<div class="signature"><span class="keyword">def</span> <span class="param">handle</span>(command: PlaceOrder) <span class="arrow">-&gt;</span> <span class="type">None</span></div>

### GetOrderHandler

- **Type:** `QueryHandler`
- **Contract:** `GetOrder`
- **Session:** `PostgresSession`

**Handle method:**

<div class="signature"><span class="keyword">def</span> <span class="param">handle</span>(query: GetOrder) <span class="arrow">-&gt;</span> <span class="type">Order | None</span></div>

### CancelOrderHandler

- **Type:** `CommandHandler`
- **Contract:** `CancelOrder`
- **Session:** `PostgresSession`

**Handle method:**

<div class="signature"><span class="keyword">def</span> <span class="param">handle</span>(command: CancelOrder) <span class="arrow">-&gt;</span> <span class="type">None</span></div>

### ListOrdersHandler

- **Type:** `QueryHandler`
- **Contract:** `ListOrders`
- **Session:** `RedisSession`

**Handle method:**

<div class="signature"><span class="keyword">def</span> <span class="param">handle</span>(query: ListOrders) <span class="arrow">-&gt;</span> <span class="type">list\[Order\]</span></div>

## Sessions

### RedisSession

### PostgresSession

### Session

## Ports

### FakeUnitOfWork

- **Type:** `FakeUnitOfWork`

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">begin</span>() <span class="arrow">-&gt;</span> <span class="type">None</span></div>
<div class="signature"><span class="keyword">def</span> <span class="param">commit</span>() <span class="arrow">-&gt;</span> <span class="type">None</span></div>
<div class="signature"><span class="keyword">def</span> <span class="param">rollback</span>() <span class="arrow">-&gt;</span> <span class="type">None</span></div>

### SmtpSender

- **Type:** `SmtpSender`

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">send</span>(to: str, subject: str, body: str) <span class="arrow">-&gt;</span> <span class="type">None</span></div>

### StripeGateway

- **Type:** `StripeGateway`

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">charge</span>(amount: float, token: str) <span class="arrow">-&gt;</span> <span class="type">bool</span></div>

### FakeInventory

- **Type:** `FakeInventory`

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">reserve</span>(product_id: str, quantity: int) <span class="arrow">-&gt;</span> <span class="type">bool</span></div>

## Projections

### OrderSummaryProjection

- **Type:** `ReadProjection`
- **Session:** `Session`

**Read method:**

<div class="signature"><span class="keyword">def</span> <span class="param">read</span>(model: object) <span class="arrow">-&gt;</span> <span class="type">list\[dict\]</span></div>

### ArchiveOrdersProjection

- **Type:** `WriteProjection`
- **Session:** `Session`

**Write method:**

<div class="signature"><span class="keyword">def</span> <span class="param">write</span>(model: object) <span class="arrow">-&gt;</span> <span class="type">None</span></div>

