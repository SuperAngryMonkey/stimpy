# ADR 0001 — Hardcode the entire order

**Status:** Accepted
**Date:** 2026-05-27

## Context

Stimpy is a proof of concept whose goal is to demonstrate end-to-end ordering
through the unofficial Domino's API from a self-hosted LXC. The user always
orders the same pizza.

## Decision

The complete order — pizza, toppings, store, customer, service method,
payment — is hardcoded in `config.py`. No database, no order composer UI, no
environment configuration.

## Consequences

- (+) Zero config surface, zero config bugs, single source of truth.
- (+) Ships immediately; the button works on first deploy.
- (-) Changing the order requires a file edit + service restart.
- (-) Only one order is possible. "Repeat last order" is trivially satisfied
  because there is only ever one order.
- A future SQLite-backed saved-order layer is the documented upgrade path if
  this graduates beyond POC (see ADR 0003).
