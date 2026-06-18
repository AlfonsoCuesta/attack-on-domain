---
hide:
  - navigation
  - toc
---

# Invoicing

1 root entity, 1 value object, 1 use case

<div class="home-features">
  <div class="feature-card">
    <h3><a href="glossary/">Glossary</a></h3>
    <p>Domain terms, entities, value objects, and services</p>
  </div>
  <div class="feature-card">
    <h3><a href="entities/">Domain Entities</a></h3>
    <p>Root entities, entities, value objects, and services</p>
  </div>
  <div class="feature-card">
    <h3><a href="infrastructure/">Infrastructure</a></h3>
    <p>Handlers, sessions, ports, and projections</p>
  </div>
</div>

## Use Cases

### InvoiceUseCase

**Ports:**

- `create_invoice`: `CommandPort[CreateInvoice]`
- `get_invoice`: `QueryPort[GetInvoice]`

**Parameters:**

<table class="param-table">
<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
<tr><td>args</td><td><code>Any</code></td><td></td><td></td></tr>
<tr><td>kwargs</td><td><code>Any</code></td><td></td><td></td></tr>
</table>


## Projections

### InvoiceReportProjection

**Type:** `ReadProjection`

**Session:** `Session`

