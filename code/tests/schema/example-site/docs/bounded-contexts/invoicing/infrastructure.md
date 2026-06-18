---
hide:
  - navigation
  - toc
---

# Invoicing — Infrastructure

## Handlers

### CreateInvoiceHandler

- **Type:** `CommandHandler`
- **Contract:** `CreateInvoice`
- **Session:** `PostgresSession`

**Handle method:**

<div class="signature"><span class="keyword">def</span> <span class="param">handle</span>(command: CreateInvoice) <span class="arrow">-&gt;</span> <span class="type">None</span></div>

### GetInvoiceHandler

- **Type:** `QueryHandler`
- **Contract:** `GetInvoice`
- **Session:** `PostgresSession`

**Handle method:**

<div class="signature"><span class="keyword">def</span> <span class="param">handle</span>(query: GetInvoice) <span class="arrow">-&gt;</span> <span class="type">Invoice | None</span></div>

## Sessions

### PostgresSession

### Session

## Ports

### FakeUnitOfWork

- **Type:** `FakeUnitOfWork`

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">begin</span>() <span class="arrow">-&gt;</span> <span class="type">None</span></div>
<div class="signature"><span class="keyword">def</span> <span class="param">commit</span>() <span class="arrow">-&gt;</span> <span class="type">None</span></div>
<div class="signature"><span class="keyword">def</span> <span class="param">rollback</span>() <span class="arrow">-&gt;</span> <span class="type">None</span></div>

### ConsoleAuditLogger

- **Type:** `ConsoleAuditLogger`

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">log</span>(action: str, details: dict) <span class="arrow">-&gt;</span> <span class="type">None</span></div>

## Projections

### InvoiceReportProjection

- **Type:** `ReadProjection`
- **Session:** `Session`

**Read method:**

<div class="signature"><span class="keyword">def</span> <span class="param">read</span>(model: object) <span class="arrow">-&gt;</span> <span class="type">list\[dict\]</span></div>

