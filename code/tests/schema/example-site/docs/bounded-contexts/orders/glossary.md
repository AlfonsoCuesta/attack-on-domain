---
hide:
  - navigation
  - toc
---

# Orders — Glossary

## Root Entities

- **Order**
  - Root aggregate for the ordering subdomain.

## Value Objects

- **OrderId**
  - Unique identifier for an order in the system.
- **OrderLine**
  - A single product line within an order.

## Services

- **PricingService**
  - Applies discount codes and calculates final prices.
- **TaxService**
  - Calculates tax amounts based on region and price.

