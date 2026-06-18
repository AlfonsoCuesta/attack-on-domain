---
hide:
  - navigation
  - toc
---

# Invoicing — Domain Entities

## Invoice

Root aggregate for the invoicing subdomain.

**Fields:**

<table class="param-table">
<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
<tr><td>id</td><td><code>str</code></td><td></td><td></td></tr>
<tr><td>order_id</td><td><code>OrderId</code></td><td></td><td></td></tr>
<tr><td>amount</td><td><code>float</code></td><td>0.0</td><td></td></tr>
<tr><td>paid</td><td><code>bool</code></td><td>False</td><td></td></tr>
</table>

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">mark_paid</span>() <span class="arrow">-&gt;</span> <span class="type">None</span></div>

**Commands:** `CreateInvoice`

**Queries:** `GetInvoice`

## OrderId

Unique identifier for an order in the system.

**Fields:**

<table class="param-table">
<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
<tr><td>value</td><td><code>str</code></td><td></td><td></td></tr>
</table>

