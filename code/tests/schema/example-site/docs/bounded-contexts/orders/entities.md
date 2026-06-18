---
hide:
  - navigation
  - toc
---

# Orders — Domain Entities

## Order

**Fields:**

<table class="param-table">
<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
<tr><td>id</td><td><code>OrderId</code></td><td></td><td></td></tr>
<tr><td>customer_id</td><td><code>CustomerId</code></td><td></td><td></td></tr>
<tr><td>lines</td><td><code>list[OrderLine]</code></td><td>[]</td><td></td></tr>
<tr><td>total</td><td><code>float</code></td><td>0.0</td><td></td></tr>
</table>

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">add_line</span>(product_id: str, quantity: int, price: float) <span class="arrow">-&gt;</span> <span class="type">None</span></div>
<div class="signature"><span class="keyword">def</span> <span class="param">calculate_total</span>() <span class="arrow">-&gt;</span> <span class="type">float</span></div>

**Commands:** `PlaceOrder`, `CancelOrder`

**Queries:** `GetOrder`, `ListOrders`

## CustomerId

**Fields:**

<table class="param-table">
<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
<tr><td>value</td><td><code>str</code></td><td></td><td></td></tr>
</table>

## OrderLine

**Fields:**

<table class="param-table">
<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
<tr><td>product_id</td><td><code>str</code></td><td></td><td></td></tr>
<tr><td>quantity</td><td><code>int</code></td><td></td><td></td></tr>
<tr><td>price</td><td><code>float</code></td><td></td><td></td></tr>
</table>

## OrderId

**Fields:**

<table class="param-table">
<tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
<tr><td>value</td><td><code>str</code></td><td></td><td></td></tr>
</table>

## PricingService

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">apply_discount</span>(base: float, code: str) <span class="arrow">-&gt;</span> <span class="type">float</span></div>

## TaxService

**Methods:**

<div class="signature"><span class="keyword">def</span> <span class="param">calculate_tax</span>(amount: float, region: str) <span class="arrow">-&gt;</span> <span class="type">float</span></div>

